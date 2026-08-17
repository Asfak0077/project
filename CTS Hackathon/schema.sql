-- ==========================================================
-- AWS RDS MySQL Database Schema
-- Project: CTS Hackathon Product Assistant
-- Database: my_project
-- Character Set: utf8mb4 (Full Unicode Support)
-- ==========================================================

CREATE DATABASE IF NOT EXISTS my_project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE my_project;

-- ----------------------------------------------------------
-- 1. USERS TABLE
-- Supports local authentication and Google OAuth linking
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NULL,
    name VARCHAR(100) NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NULL,
    auth_provider VARCHAR(50) DEFAULT 'local',
    google_id VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_google (google_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 2. SEARCH HISTORY TABLE
-- Stores user search logs with query filters
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_history (
    search_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    query_text VARCHAR(500) NOT NULL,
    filters_applied JSON NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_search_user (user_id),
    INDEX idx_search_time (searched_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 3. COMPARISON HISTORY TABLE
-- Stores side-by-side product comparison records
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS comparison_history (
    comparison_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    compared_products JSON NOT NULL,
    notes_or_summary TEXT NULL,
    compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_comp_user (user_id),
    INDEX idx_comp_time (compared_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 4. RECOMMENDATION HISTORY TABLE
-- Stores AI recommendation queries and results
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS recommendation_history (
    recommendation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    user_requirements TEXT NULL,
    recommended_products JSON NOT NULL,
    reasoning_summary TEXT NULL,
    recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rec_user (user_id),
    INDEX idx_rec_time (recommended_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 5. LAPTOPS CATALOG TABLE
-- Product catalog with full hardware specifications
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS laptops (
    laptop_id VARCHAR(100) PRIMARY KEY,
    `Brand` VARCHAR(100) NULL,
    `Model` VARCHAR(255) NULL,
    `Company` VARCHAR(100) NULL,
    `1 stars` INT DEFAULT 0,
    `2 stars` INT DEFAULT 0,
    `3 stars` INT DEFAULT 0,
    `4 stars` INT DEFAULT 0,
    `5 stars` INT DEFAULT 0,
    `SSD` VARCHAR(255) NULL,
    `Colours` VARCHAR(100) NULL,
    `Operating system` VARCHAR(100) NULL,
    `Hard disk` VARCHAR(255) NULL,
    `Model Number` VARCHAR(255) NULL,
    `Processor` VARCHAR(255) NULL,
    `Graphics Processor` VARCHAR(255) NULL,
    `Dedicated Graphics` VARCHAR(255) NULL,
    `Finger Print Sensor` VARCHAR(50) NULL,
    `Resolution` VARCHAR(100) NULL,
    `Wi-Fi standards supported` VARCHAR(255) NULL,
    `Weight (kg)` DOUBLE NULL,
    `Dimensions (mm)` VARCHAR(255) NULL,
    `Bluetooth version` VARCHAR(50) NULL,
    `Number of USB Ports` VARCHAR(50) NULL,
    `Series` VARCHAR(100) NULL,
    `Internal Mic` VARCHAR(50) NULL,
    `Touch Screen` VARCHAR(50) NULL,
    `Product Name` VARCHAR(255) NULL,
    `Touchpad` VARCHAR(100) NULL,
    `Battery Cell` VARCHAR(100) NULL,
    `Pointer Device` VARCHAR(100) NULL,
    `USB Ports` VARCHAR(255) NULL,
    `Cache` VARCHAR(100) NULL,
    `Mic In` VARCHAR(50) NULL,
    `Speakers` VARCHAR(255) NULL,
    `Multi Card Slot` VARCHAR(100) NULL,
    `RJ45 (LAN)` VARCHAR(50) NULL,
    `HDMI Port` VARCHAR(50) NULL,
    `Ethernet` VARCHAR(50) NULL,
    `Price_Clean` DOUBLE NULL,
    `RAM_GB` DOUBLE NULL,
    `Screen_Size_inch` DOUBLE NULL,
    `Base_Clock_Speed_GHz` DOUBLE NULL,
    `Total_Ratings` DOUBLE NULL,
    INDEX idx_laptop_brand (`Brand`),
    INDEX idx_laptop_price (`Price_Clean`),
    INDEX idx_laptop_ram (`RAM_GB`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 6. SEED DATA FOR TESTING
-- Initial demo and test accounts
-- ----------------------------------------------------------
INSERT INTO users (user_id, username, name, email, auth_provider) VALUES 
(1, 'demo_user', 'Demo User', 'demo@example.com', 'local'), 
(2, 'test_user', 'Test User', 'test@example.com', 'local')
ON DUPLICATE KEY UPDATE 
    username = VALUES(username),
    name = VALUES(name);