import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="Laptop")

    products = relationship("Product", back_populates="category_rel")

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    logo_url = Column(String(500), nullable=True)

    products = relationship("Product", back_populates="brand_rel")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(100), unique=True, index=True, nullable=False)  # e.g., 'LAP_001' or unique hash
    name = Column(String(255), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    brand = Column(String(100), nullable=False, index=True)
    category = Column(String(100), default="Laptop", index=True)
    model = Column(String(255), nullable=True)
    price = Column(Float, nullable=False, index=True)
    original_price = Column(Float, nullable=True)
    rating = Column(Float, default=4.0, index=True)
    total_ratings = Column(Integer, default=0)
    reviews_count = Column(Integer, default=0)
    image_url = Column(String(500), nullable=True)
    badge = Column(String(50), nullable=True)
    specs_summary = Column(Text, nullable=True)
    score = Column(Float, default=85.0, index=True)  # Overall AI Benchmark Score
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    brand_rel = relationship("Brand", back_populates="products")
    category_rel = relationship("Category", back_populates="products")
    specs = relationship("ProductSpec", back_populates="product", uselist=False, cascade="all, delete-orphan")
    features = relationship("ProductFeature", back_populates="product", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="product", cascade="all, delete-orphan")
    recommendation_items = relationship("RecommendationItem", back_populates="product", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_product_brand_price", "brand", "price"),
        Index("idx_product_category_price", "category", "price"),
    )

class ProductSpec(Base):
    __tablename__ = "product_specs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    cpu = Column(String(255), nullable=True, index=True)
    ram_gb = Column(Float, nullable=True, index=True)
    storage = Column(String(255), nullable=True)
    gpu = Column(String(255), nullable=True)
    display_size_inch = Column(Float, nullable=True)
    resolution = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    weight_kg = Column(Float, nullable=True)
    battery = Column(String(100), nullable=True)
    base_clock_speed_ghz = Column(Float, nullable=True)
    touch_screen = Column(Boolean, default=False)
    ports = Column(Text, nullable=True)
    raw_specs_json = Column(JSON, nullable=True)

    product = relationship("Product", back_populates="specs")

class ProductFeature(Base):
    __tablename__ = "product_features"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_type = Column(String(50), nullable=False)  # 'pro', 'con', 'fps', 'highlight'
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)

    product = relationship("Product", back_populates="features")
