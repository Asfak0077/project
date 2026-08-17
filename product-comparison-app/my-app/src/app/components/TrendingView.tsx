"use client";

import React from "react";
import { motion } from "framer-motion";
import { TrendingUp, Flame, ArrowUpRight, Scale, ArrowLeft, Star, Heart } from "lucide-react";
import { Product } from "./HomeView";

interface TrendingViewProps {
    onCompare: (products: Product[]) => void;
    shortlisted: Product[];
    setShortlisted: React.Dispatch<React.SetStateAction<Product[]>>;
    wishlist: Product[];
    toggleWishlist: (product: Product) => void;
    onBack: () => void;
}

const TRENDING_ITEMS = [
    {
        id: "LAP_001",
        brand: "ASUS",
        name: "Vivobook 16 OLED",
        category: "Laptop",
        price: 64990,
        cpu: "Intel Core i7 13th Gen",
        ram: 16,
        storage: "512 GB SSD",
        gpu: "NVIDIA RTX 3050",
        score: 94,
        image: "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
        rating: 4.7,
        searches: "142,500+",
        rank: 1,
        hotness: "Extreme",
    },
    {
        id: "LAP_006",
        brand: "MSI",
        name: "Modern 15 B13M",
        category: "Laptop",
        price: 72990,
        cpu: "Intel Core i7 13th Gen",
        ram: 16,
        storage: "1 TB SSD",
        gpu: "NVIDIA RTX 4060",
        score: 91,
        image: "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&auto=format&fit=crop&q=80",
        rating: 4.6,
        searches: "98,200+",
        rank: 2,
        hotness: "High",
    },
    {
        id: "LAP_002",
        brand: "HP",
        name: "Pavilion 15 Gaming",
        category: "Laptop",
        price: 68290,
        cpu: "AMD Ryzen 7 7735HS",
        ram: 16,
        storage: "512 GB SSD",
        gpu: "NVIDIA RTX 4050",
        score: 89,
        image: "https://images.unsplash.com/photo-1544731612-de292439cc67?w=600&auto=format&fit=crop&q=80",
        rating: 4.5,
        searches: "87,400+",
        rank: 3,
        hotness: "High",
    },
    {
        id: "LAP_005",
        brand: "Acer",
        name: "Aspire 5 Slim",
        category: "Laptop",
        price: 55990,
        cpu: "Intel Core i5 13th Gen",
        ram: 16,
        storage: "512 GB SSD",
        gpu: "NVIDIA RTX 2050",
        score: 86,
        image: "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
        rating: 4.3,
        searches: "64,100+",
        rank: 4,
        hotness: "Medium",
    },
];

export default function TrendingView({
    onCompare,
    shortlisted,
    setShortlisted,
    wishlist,
    toggleWishlist,
    onBack,
}: TrendingViewProps) {
    const toggleShortlist = (prod: Product) => {
        if (shortlisted.some((p) => p.id === prod.id)) {
            setShortlisted(shortlisted.filter((p) => p.id !== prod.id));
        } else {
            setShortlisted([...shortlisted, prod]);
        }
    };

    return (
        <div className="py-8 space-y-8 pb-32">
            {/* Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
                <div>
                    <button onClick={onBack} className="flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-brand-600 mb-2 transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back
                    </button>
                    <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
                        Trending Hardware <Flame className="w-7 h-7 text-amber-500 fill-amber-500" />
                    </h1>
                    <p className="text-slate-600 text-sm font-medium mt-1">
                        Top searched and compared gadgets across our RAG comparison graph this week.
                    </p>
                </div>
            </div>

            {/* Ranked List */}
            <div className="space-y-4">
                {TRENDING_ITEMS.map((item, i) => {
                    const isSelected = shortlisted.some((p) => p.id === item.id);
                    const isWishlisted = wishlist.some((p) => p.id === item.id);

                    return (
                        <motion.div
                            key={item.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className="bg-white border border-slate-200/90 rounded-3xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-sm hover:shadow-xl transition-all"
                        >
                            <div className="flex items-center gap-5">
                                {/* Rank Badge */}
                                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-600 to-indigo-600 flex items-center justify-center font-black text-xl text-white shadow-md shrink-0">
                                    #{item.rank}
                                </div>

                                <div className="w-20 h-20 rounded-2xl overflow-hidden bg-slate-100 shrink-0">
                                    <img src={item.image} alt={item.name} className="w-full h-full object-cover" />
                                </div>

                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-[10px] font-extrabold uppercase tracking-wider text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md border border-brand-100">
                                            {item.brand}
                                        </span>
                                        <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md flex items-center gap-1 border border-amber-200">
                                            <Flame className="w-3 h-3 text-amber-500" /> {item.hotness} Search Interest
                                        </span>
                                    </div>
                                    <h3 className="font-extrabold text-slate-900 text-lg">{item.name}</h3>
                                    <p className="text-xs text-slate-500 font-semibold mt-0.5">{item.cpu} • {item.ram}GB RAM</p>
                                </div>
                            </div>

                            <div className="flex items-center gap-6 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 pt-4 md:pt-0 border-slate-100">
                                <div className="text-right">
                                    <div className="text-xl font-black text-slate-900">₹{item.price.toLocaleString()}</div>
                                    <div className="text-xs font-bold text-slate-500 flex items-center gap-1 justify-end mt-0.5">
                                        <ArrowUpRight className="w-3.5 h-3.5 text-emerald-600" /> {item.searches} views
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => toggleWishlist(item)}
                                        className={`p-3 rounded-xl border transition-colors ${isWishlisted
                                                ? "bg-rose-50 text-rose-600 border-rose-200"
                                                : "bg-slate-50 text-slate-600 border-slate-200 hover:text-rose-600"
                                            }`}
                                    >
                                        <Heart className={`w-4 h-4 ${isWishlisted ? "fill-rose-600" : ""}`} />
                                    </button>

                                    <button
                                        onClick={() => toggleShortlist(item)}
                                        className={`flex items-center gap-2 px-5 py-3 rounded-xl text-xs font-bold transition-all ${isSelected
                                                ? "bg-brand-600 text-white shadow-md shadow-brand-500/20"
                                                : "bg-slate-100 text-slate-800 hover:bg-brand-50 hover:text-brand-600 border border-slate-200"
                                            }`}
                                    >
                                        <Scale className="w-4 h-4" />
                                        {isSelected ? "Selected" : "Add Compare"}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
