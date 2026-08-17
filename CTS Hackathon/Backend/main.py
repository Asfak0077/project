import os
import sys
from pathlib import Path
from typing import Optional, List
import datetime
import mysql.connector
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt

# Add parent directory to sys.path to import db module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import (
    get_db_connection,
    get_db_cursor,
    get_user_by_email,
    get_user_by_id,
    get_all_users as fetch_all_users_from_db,
    update_user as update_user_in_db,
    delete_user as delete_user_from_db,
    log_user_search,
    log_user_comparison,
    log_user_recommendation,
)

app = FastAPI(title="CTS Hackathon API", description="AWS RDS MySQL Powered Product Assistant Backend")

# Auth Configuration from Environment Variables
SECRET_KEY = os.getenv("JWT_SECRET", "versus_ai_super_secret_jwt_key_2026_change_in_production")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "464500510198-luj97ikpbik34hcvaro2aip272uv7te9.apps.googleusercontent.com")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------- AUTH & USER SCHEMAS -------------------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthSchema(BaseModel):
    credential: str  # Google ID Token sent from client

class UserUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password_hash: Optional[str] = None

# Helper to generate JWT Token
def create_jwt_token(user_id: int, email: str):
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# ------------------- AUTH ENDPOINTS -------------------

# 1. LOCAL REGISTRATION
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: UserCreate):
    try:
        clean_email = user.email.lower().strip()
        existing = get_user_by_email(clean_email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        hashed_password = pwd_context.hash(user.password)
        with get_db_cursor(commit=True) as cursor:
            sql = "INSERT INTO users (name, username, email, password_hash, auth_provider) VALUES (%s, %s, %s, %s, 'local')"
            cursor.execute(sql, (user.name.strip(), user.name.strip(), clean_email, hashed_password))
            user_id = cursor.lastrowid
        
        token = create_jwt_token(int(user_id or 0), clean_email)
        return {"token": token, "name": user.name, "email": clean_email, "user_id": user_id}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. LOCAL LOGIN
@app.post("/api/auth/login", tags=["Authentication"])
def login_user(user: UserLogin):
    try:
        clean_email = user.email.lower().strip()
        db_user = get_user_by_email(clean_email)
        
        if not db_user or not db_user.get("password_hash") or not pwd_context.verify(user.password, db_user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        token = create_jwt_token(int(db_user["user_id"]), db_user["email"])
        user_name = db_user.get("name") or db_user.get("username") or clean_email.split("@")[0]
        return {"token": token, "name": user_name, "email": db_user["email"], "user_id": db_user["user_id"]}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. GOOGLE OAUTH LOGIN / SIGNUP
@app.post("/api/auth/google", tags=["Authentication"])
def google_auth(data: GoogleAuthSchema):
    try:
        id_info = id_token.verify_oauth2_token(data.credential, requests.Request(), GOOGLE_CLIENT_ID)
        google_id = id_info["sub"]
        email = id_info["email"].lower().strip()
        name = id_info.get("name", email.split("@")[0])
        
        db_user = get_user_by_email(email)
        
        if not db_user:
            with get_db_cursor(commit=True) as cursor:
                sql = "INSERT INTO users (name, username, email, google_id, auth_provider) VALUES (%s, %s, %s, %s, 'google')"
                cursor.execute(sql, (name, name, email, google_id))
                user_id = int(cursor.lastrowid or 0)
        else:
            user_id = int(db_user["user_id"])
            if not db_user.get("google_id"):
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("UPDATE users SET google_id = %s WHERE user_id = %s", (google_id, user_id))
            
        token = create_jwt_token(user_id, email)
        return {"token": token, "name": name, "email": email, "user_id": user_id}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------- USERS ENDPOINTS -------------------

@app.get("/users", tags=["Users"])
def get_all_users():
    try:
        users = fetch_all_users_from_db()
        return users
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}", tags=["Users"])
def get_user_by_id_endpoint(user_id: int):
    try:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # Remove password hash from response for security
        user.pop("password_hash", None)
        return user
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/users/{user_id}", tags=["Users"])
def update_user_endpoint(user_id: int, user: UserUpdate):
    try:
        update_data = user.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update.")

        if "password_hash" in update_data and update_data["password_hash"]:
            update_data["password_hash"] = pwd_context.hash(update_data["password_hash"])

        success = update_user_in_db(user_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="User not found or no changes made")

        return {"message": f"User ID '{user_id}' updated successfully!"}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/users/{user_id}", tags=["Users"])
def delete_user_endpoint(user_id: int):
    try:
        success = delete_user_from_db(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": f"User ID '{user_id}' deleted successfully!"}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------- LAPTOP SCHEMAS & ENDPOINTS -------------------

COLUMN_MAPPING = {
    "brand": "Brand",
    "model": "Model",
    "company": "Company",
    "stars_1": "1 stars",
    "stars_2": "2 stars",
    "stars_3": "3 stars",
    "stars_4": "4 stars",
    "stars_5": "5 stars",
    "ssd": "SSD",
    "colours": "Colours",
    "operating_system": "Operating system",
    "hard_disk": "Hard disk",
    "model_number": "Model Number",
    "processor": "Processor",
    "graphics_processor": "Graphics Processor",
    "dedicated_graphics": "Dedicated Graphics",
    "finger_print_sensor": "Finger Print Sensor",
    "resolution": "Resolution",
    "wifi_standards_supported": "Wi-Fi standards supported",
    "weight_kg": "Weight (kg)",
    "dimensions_mm": "Dimensions (mm)",
    "bluetooth_version": "Bluetooth version",
    "number_of_usb_ports": "Number of USB Ports",
    "series": "Series",
    "internal_mic": "Internal Mic",
    "touch_screen": "Touch Screen",
    "product_name": "Product Name",
    "touchpad": "Touchpad",
    "battery_cell": "Battery Cell",
    "pointer_device": "Pointer Device",
    "usb_ports": "USB Ports",
    "cache": "Cache",
    "mic_in": "Mic In",
    "speakers": "Speakers",
    "multi_card_slot": "Multi Card Slot",
    "rj45_lan": "RJ45 (LAN)",
    "hdmi_port": "HDMI Port",
    "ethernet": "Ethernet",
    "price_clean": "Price_Clean",
    "ram_gb": "RAM_GB",
    "screen_size_inch": "Screen_Size_inch",
    "base_clock_speed_ghz": "Base_Clock_Speed_GHz",
    "total_ratings": "Total_Ratings"
}

class LaptopSchema(BaseModel):
    laptop_id: str
    brand: Optional[str] = Field(default=None, alias="Brand")
    model: Optional[str] = Field(default=None, alias="Model")
    company: Optional[str] = Field(default=None, alias="Company")
    stars_1: Optional[int] = Field(default=None, alias="1 stars")
    stars_2: Optional[int] = Field(default=None, alias="2 stars")
    stars_3: Optional[int] = Field(default=None, alias="3 stars")
    stars_4: Optional[int] = Field(default=None, alias="4 stars")
    stars_5: Optional[int] = Field(default=None, alias="5 stars")
    ssd: Optional[str] = Field(default=None, alias="SSD")
    colours: Optional[str] = Field(default=None, alias="Colours")
    operating_system: Optional[str] = Field(default=None, alias="Operating system")
    hard_disk: Optional[str] = Field(default=None, alias="Hard disk")
    model_number: Optional[str] = Field(default=None, alias="Model Number")
    processor: Optional[str] = Field(default=None, alias="Processor")
    graphics_processor: Optional[str] = Field(default=None, alias="Graphics Processor")
    dedicated_graphics: Optional[str] = Field(default=None, alias="Dedicated Graphics")
    finger_print_sensor: Optional[str] = Field(default=None, alias="Finger Print Sensor")
    resolution: Optional[str] = Field(default=None, alias="Resolution")
    wifi_standards_supported: Optional[str] = Field(default=None, alias="Wi-Fi standards supported")
    weight_kg: Optional[float] = Field(default=None, alias="Weight (kg)")
    dimensions_mm: Optional[str] = Field(default=None, alias="Dimensions (mm)")
    bluetooth_version: Optional[str] = Field(default=None, alias="Bluetooth version")
    number_of_usb_ports: Optional[str] = Field(default=None, alias="Number of USB Ports")
    series: Optional[str] = Field(default=None, alias="Series")
    internal_mic: Optional[str] = Field(default=None, alias="Internal Mic")
    touch_screen: Optional[str] = Field(default=None, alias="Touch Screen")
    product_name: Optional[str] = Field(default=None, alias="Product Name")
    touchpad: Optional[str] = Field(default=None, alias="Touchpad")
    battery_cell: Optional[str] = Field(default=None, alias="Battery Cell")
    pointer_device: Optional[str] = Field(default=None, alias="Pointer Device")
    usb_ports: Optional[str] = Field(default=None, alias="USB Ports")
    cache: Optional[str] = Field(default=None, alias="Cache")
    mic_in: Optional[str] = Field(default=None, alias="Mic In")
    speakers: Optional[str] = Field(default=None, alias="Speakers")
    multi_card_slot: Optional[str] = Field(default=None, alias="Multi Card Slot")
    rj45_lan: Optional[str] = Field(default=None, alias="RJ45 (LAN)")
    hdmi_port: Optional[str] = Field(default=None, alias="HDMI Port")
    ethernet: Optional[str] = Field(default=None, alias="Ethernet")
    price_clean: Optional[float] = Field(default=None, alias="Price_Clean")
    ram_gb: Optional[float] = Field(default=None, alias="RAM_GB")
    screen_size_inch: Optional[float] = Field(default=None, alias="Screen_Size_inch")
    base_clock_speed_ghz: Optional[float] = Field(default=None, alias="Base_Clock_Speed_GHz")
    total_ratings: Optional[float] = Field(default=None, alias="Total_Ratings")

    class Config:
        populate_by_name = True

class LaptopUpdateSchema(BaseModel):
    brand: Optional[str] = Field(default=None, alias="Brand")
    model: Optional[str] = Field(default=None, alias="Model")
    company: Optional[str] = Field(default=None, alias="Company")
    stars_1: Optional[int] = Field(default=None, alias="1 stars")
    stars_2: Optional[int] = Field(default=None, alias="2 stars")
    stars_3: Optional[int] = Field(default=None, alias="3 stars")
    stars_4: Optional[int] = Field(default=None, alias="4 stars")
    stars_5: Optional[int] = Field(default=None, alias="5 stars")
    ssd: Optional[str] = Field(default=None, alias="SSD")
    colours: Optional[str] = Field(default=None, alias="Colours")
    operating_system: Optional[str] = Field(default=None, alias="Operating system")
    hard_disk: Optional[str] = Field(default=None, alias="Hard disk")
    model_number: Optional[str] = Field(default=None, alias="Model Number")
    processor: Optional[str] = Field(default=None, alias="Processor")
    graphics_processor: Optional[str] = Field(default=None, alias="Graphics Processor")
    dedicated_graphics: Optional[str] = Field(default=None, alias="Dedicated Graphics")
    finger_print_sensor: Optional[str] = Field(default=None, alias="Finger Print Sensor")
    resolution: Optional[str] = Field(default=None, alias="Resolution")
    wifi_standards_supported: Optional[str] = Field(default=None, alias="Wi-Fi standards supported")
    weight_kg: Optional[float] = Field(default=None, alias="Weight (kg)")
    dimensions_mm: Optional[str] = Field(default=None, alias="Dimensions (mm)")
    bluetooth_version: Optional[str] = Field(default=None, alias="Bluetooth version")
    number_of_usb_ports: Optional[str] = Field(default=None, alias="Number of USB Ports")
    series: Optional[str] = Field(default=None, alias="Series")
    internal_mic: Optional[str] = Field(default=None, alias="Internal Mic")
    touch_screen: Optional[str] = Field(default=None, alias="Touch Screen")
    product_name: Optional[str] = Field(default=None, alias="Product Name")
    touchpad: Optional[str] = Field(default=None, alias="Touchpad")
    battery_cell: Optional[str] = Field(default=None, alias="Battery Cell")
    pointer_device: Optional[str] = Field(default=None, alias="Pointer Device")
    usb_ports: Optional[str] = Field(default=None, alias="USB Ports")
    cache: Optional[str] = Field(default=None, alias="Cache")
    mic_in: Optional[str] = Field(default=None, alias="Mic In")
    speakers: Optional[str] = Field(default=None, alias="Speakers")
    multi_card_slot: Optional[str] = Field(default=None, alias="Multi Card Slot")
    rj45_lan: Optional[str] = Field(default=None, alias="RJ45 (LAN)")
    hdmi_port: Optional[str] = Field(default=None, alias="HDMI Port")
    ethernet: Optional[str] = Field(default=None, alias="Ethernet")
    price_clean: Optional[float] = Field(default=None, alias="Price_Clean")
    ram_gb: Optional[float] = Field(default=None, alias="RAM_GB")
    screen_size_inch: Optional[float] = Field(default=None, alias="Screen_Size_inch")
    base_clock_speed_ghz: Optional[float] = Field(default=None, alias="Base_Clock_Speed_GHz")
    total_ratings: Optional[float] = Field(default=None, alias="Total_Ratings")

    class Config:
        populate_by_name = True

@app.get("/laptops", tags=["Laptops"])
def get_all_laptops(limit: int = 20, offset: int = 0):
    try:
        with get_db_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM laptops LIMIT %s OFFSET %s", (limit, offset))
            laptops = cursor.fetchall()
        return laptops
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/laptops/{laptop_id}", tags=["Laptops"])
def get_laptop_by_id(laptop_id: str):
    try:
        with get_db_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM laptops WHERE laptop_id = %s", (laptop_id,))
            laptop = cursor.fetchone()

        if not laptop:
            raise HTTPException(status_code=404, detail="Laptop not found")
        return laptop
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/laptops", status_code=status.HTTP_201_CREATED, tags=["Laptops"])
def create_laptop(laptop: LaptopSchema):
    try:
        sql = """
            INSERT INTO laptops (
                laptop_id, `Brand`, `Model`, `Company`, `1 stars`, `2 stars`, `4 stars`, `3 stars`, `5 stars`,
                `SSD`, `Colours`, `Operating system`, `Hard disk`, `Model Number`, `Processor`,
                `Graphics Processor`, `Dedicated Graphics`, `Finger Print Sensor`, `Resolution`,
                `Wi-Fi standards supported`, `Weight (kg)`, `Dimensions (mm)`, `Bluetooth version`,
                `Number of USB Ports`, `Series`, `Internal Mic`, `Touch Screen`, `Product Name`,
                `Touchpad`, `Battery Cell`, `Pointer Device`, `USB Ports`, `Cache`, `Mic In`,
                `Speakers`, `Multi Card Slot`, `RJ45 (LAN)`, `HDMI Port`, `Ethernet`, `Price_Clean`,
                `RAM_GB`, `Screen_Size_inch`, `Base_Clock_Speed_GHz`, `Total_Ratings`
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        values = (
            laptop.laptop_id, laptop.brand, laptop.model, laptop.company,
            laptop.stars_1, laptop.stars_2, laptop.stars_4, laptop.stars_3, laptop.stars_5,
            laptop.ssd, laptop.colours, laptop.operating_system, laptop.hard_disk, laptop.model_number,
            laptop.processor, laptop.graphics_processor, laptop.dedicated_graphics, laptop.finger_print_sensor,
            laptop.resolution, laptop.wifi_standards_supported, laptop.weight_kg, laptop.dimensions_mm,
            laptop.bluetooth_version, laptop.number_of_usb_ports, laptop.series, laptop.internal_mic,
            laptop.touch_screen, laptop.product_name, laptop.touchpad, laptop.battery_cell, laptop.pointer_device,
            laptop.usb_ports, laptop.cache, laptop.mic_in, laptop.speakers, laptop.multi_card_slot,
            laptop.rj45_lan, laptop.hdmi_port, laptop.ethernet, laptop.price_clean, laptop.ram_gb,
            laptop.screen_size_inch, laptop.base_clock_speed_ghz, laptop.total_ratings
        )

        with get_db_cursor(commit=True) as cursor:
            cursor.execute(sql, values)

        return {"message": "Laptop created successfully!", "laptop_id": laptop.laptop_id}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/laptops/{laptop_id}", tags=["Laptops"])
def update_laptop(laptop_id: str, laptop: LaptopUpdateSchema):
    try:
        update_data = laptop.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update.")

        set_clauses = []
        values = []
        for field, value in update_data.items():
            db_col = COLUMN_MAPPING.get(field, field)
            set_clauses.append(f"`{db_col}` = %s")
            values.append(value)

        values.append(laptop_id)
        sql = f"UPDATE laptops SET {', '.join(set_clauses)} WHERE laptop_id = %s"

        with get_db_cursor(commit=True) as cursor:
            cursor.execute(sql, tuple(values))
            updated_count = cursor.rowcount

        if updated_count == 0:
            raise HTTPException(status_code=404, detail="Laptop not found")

        return {"message": f"Laptop '{laptop_id}' updated successfully!"}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/laptops/{laptop_id}", tags=["Laptops"])
def delete_laptop(laptop_id: str):
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM laptops WHERE laptop_id = %s", (laptop_id,))
            deleted_count = cursor.rowcount

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Laptop not found")

        return {"message": f"Laptop '{laptop_id}' deleted successfully!"}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))