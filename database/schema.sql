-- ===================================================
-- VersusAI Complete MySQL 8.0 / Aurora DDL Schema
-- ===================================================

CREATE DATABASE IF NOT EXISTS `my_project` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `my_project`;

-- 1. Roles
CREATE TABLE IF NOT EXISTS `roles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `description` VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Users
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(255) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NULL,
    `name` VARCHAR(150) NOT NULL,
    `role_id` INT NOT NULL DEFAULT 1,
    `auth_provider` VARCHAR(50) NOT NULL DEFAULT 'local',
    `provider_user_id` VARCHAR(255) NULL,
    `profile_image_url` VARCHAR(500) NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`role_id`) REFERENCES `roles`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. User Preferences
CREATE TABLE IF NOT EXISTS `user_preferences` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `preferred_categories` JSON NULL,
    `preferred_brands` JSON NULL,
    `min_budget` DECIMAL(12, 2) NULL,
    `max_budget` DECIMAL(12, 2) NULL,
    `primary_usage` VARCHAR(100) NULL,
    `dark_mode` BOOLEAN DEFAULT FALSE,
    `notifications_enabled` BOOLEAN DEFAULT TRUE,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Categories & Brands
CREATE TABLE IF NOT EXISTS `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `display_name` VARCHAR(150) NOT NULL,
    `icon` VARCHAR(100) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `brands` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `logo_url` VARCHAR(500) NULL,
    `country` VARCHAR(100) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Products
CREATE TABLE IF NOT EXISTS `products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `product_code` VARCHAR(100) NOT NULL UNIQUE,
    `brand` VARCHAR(100) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `category` VARCHAR(100) NOT NULL DEFAULT 'Laptop',
    `model` VARCHAR(150) NULL,
    `price` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `original_price` DECIMAL(12, 2) NULL,
    `rating` DECIMAL(3, 2) NOT NULL DEFAULT 4.00,
    `reviews_count` INT NOT NULL DEFAULT 0,
    `score` DECIMAL(5, 2) NOT NULL DEFAULT 80.00,
    `image_url` VARCHAR(1000) NULL,
    `badge` VARCHAR(100) NULL,
    `specs_summary` TEXT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_brand` (`brand`),
    INDEX `idx_category` (`category`),
    INDEX `idx_price` (`price`),
    INDEX `idx_score` (`score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Product Technical Specifications
CREATE TABLE IF NOT EXISTS `product_specs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `product_id` INT NOT NULL UNIQUE,
    `cpu` VARCHAR(200) NULL,
    `ram_gb` DECIMAL(6, 2) NULL,
    `storage` VARCHAR(200) NULL,
    `gpu` VARCHAR(200) NULL,
    `display_size_inch` DECIMAL(5, 2) NULL,
    `resolution` VARCHAR(100) NULL,
    `os` VARCHAR(100) NULL,
    `weight_kg` DECIMAL(5, 2) NULL,
    `battery` VARCHAR(200) NULL,
    `base_clock_speed_ghz` DECIMAL(4, 2) NULL,
    `touch_screen` BOOLEAN DEFAULT FALSE,
    `ports` VARCHAR(500) NULL,
    `raw_specs_json` JSON NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Product Features / Pros / Cons / FPS Benchmarks
CREATE TABLE IF NOT EXISTS `product_features` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `product_id` INT NOT NULL,
    `feature_type` VARCHAR(50) NOT NULL, -- 'pro', 'con', 'fps', 'highlight'
    `content` TEXT NOT NULL,
    `metadata_json` JSON NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Product Battles History
CREATE TABLE IF NOT EXISTS `product_battles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `product_1_id` VARCHAR(100) NOT NULL,
    `product_2_id` VARCHAR(100) NOT NULL,
    `product_1_name` VARCHAR(255) NOT NULL,
    `product_2_name` VARCHAR(255) NOT NULL,
    `winner_id` VARCHAR(100) NULL,
    `winner_name` VARCHAR(255) NULL,
    `product_1_score` DECIMAL(5, 2) NOT NULL,
    `product_2_score` DECIMAL(5, 2) NOT NULL,
    `performance_winner` VARCHAR(100) NULL,
    `price_winner` VARCHAR(100) NULL,
    `display_winner` VARCHAR(100) NULL,
    `battery_winner` VARCHAR(100) NULL,
    `rating_winner` VARCHAR(100) NULL,
    `ai_verdict` TEXT NULL,
    `confidence_score` INT NOT NULL DEFAULT 85,
    `rounds_json` JSON NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Notifications
CREATE TABLE IF NOT EXISTS `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `message` TEXT NOT NULL,
    `type` VARCHAR(50) NOT NULL DEFAULT 'INFO',
    `status` VARCHAR(20) NOT NULL DEFAULT 'unread',
    `data_json` JSON NULL,
    `read_at` TIMESTAMP NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Favorites (Wishlist)
CREATE TABLE IF NOT EXISTS `favorites` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `product_id` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_user_product_favorite` (`user_id`, `product_id`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Documents & Chunks (RAG)
CREATE TABLE IF NOT EXISTS `documents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `title` VARCHAR(255) NOT NULL,
    `filename` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_size_bytes` INT NOT NULL DEFAULT 0,
    `total_chunks` INT NOT NULL DEFAULT 0,
    `status` VARCHAR(50) NOT NULL DEFAULT 'indexed',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `document_chunks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `document_id` INT NOT NULL,
    `chunk_index` INT NOT NULL,
    `page_number` INT NULL,
    `section_title` VARCHAR(255) NULL,
    `content` LONGTEXT NOT NULL,
    `embedding_json` JSON NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`document_id`) REFERENCES `documents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
