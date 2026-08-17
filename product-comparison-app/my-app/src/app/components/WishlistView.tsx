"use client";

import React from "react";
import { motion } from "framer-motion";
import { Heart, Trash2, Scale, ArrowLeft, Cpu, Activity } from "lucide-react";
import { Product } from "../types";

interface WishlistViewProps {
  wishlist: Product[];
  toggleWishlist: (product: Product) => void;
  onCompare: (products: Product[]) => void;
  onBack: () => void;
}

export default function WishlistView({
  wishlist,
  toggleWishlist,
  onCompare,
  onBack,
}: WishlistViewProps) {
  const totalValue = wishlist.reduce((acc, p) => acc + p.price, 0);

  if (wishlist.length === 0) {
    return (
      <div className="py-24 text-center space-y-4">
        <div className="w-20 h-20 bg-rose-50 border border-rose-200 text-rose-600 rounded-3xl mx-auto flex items-center justify-center">
          <Heart className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-black text-slate-900">Your Wishlist is Empty</h2>
        <p className="text-slate-500 text-sm max-w-md mx-auto font-medium">
          Save products you&apos;re considering by clicking the heart icon on any gadget card in Discover.
        </p>
        <button
          onClick={onBack}
          className="mt-4 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl font-black text-xs shadow-md shadow-blue-500/20 hover:shadow-lg transition-all inline-flex items-center gap-2 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Explore Catalog
        </button>
      </div>
    );
  }

  return (
    <div className="py-8 space-y-8 pb-32">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-blue-600 mb-2 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            Saved Wishlist <Heart className="w-7 h-7 text-rose-500 fill-rose-500" />
          </h1>
          <p className="text-slate-500 text-xs font-semibold mt-1">
            {wishlist.length} saved products • Combined value: ₹{totalValue.toLocaleString()}
          </p>
        </div>

        <button
          onClick={() => onCompare(wishlist)}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl font-black text-xs shadow-md shadow-blue-500/20 hover:shadow-lg transition-all cursor-pointer"
        >
          <Scale className="w-4 h-4" /> Compare All ({wishlist.length})
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {wishlist.map((prod, i) => (
          <motion.div
            key={prod.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-white border border-slate-200/90 rounded-3xl p-5 flex flex-col justify-between shadow-2xs hover:shadow-xl transition-all"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-black text-blue-600 uppercase tracking-wider">{prod.brand}</span>
                <button
                  onClick={() => toggleWishlist(prod)}
                  className="p-2 text-rose-500 hover:bg-rose-50 rounded-xl transition-colors cursor-pointer"
                  title="Remove from wishlist"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="h-44 w-full rounded-2xl overflow-hidden mb-4 bg-slate-100">
                <img src={prod.image} alt={prod.name} className="w-full h-full object-cover" />
              </div>

              <h3 className="font-extrabold text-base text-slate-900 tracking-tight">{prod.name}</h3>
              <div className="text-xl font-black text-slate-900 mt-1">₹{prod.price.toLocaleString()}</div>

              <div className="grid grid-cols-2 gap-2 mt-4 text-xs font-semibold text-slate-700">
                <div className="flex items-center gap-1.5 p-2 bg-slate-50 border border-slate-200 rounded-xl">
                  <Cpu className="w-3.5 h-3.5 text-blue-600" />
                  <span className="truncate">{prod.cpu}</span>
                </div>
                <div className="flex items-center gap-1.5 p-2 bg-slate-50 border border-slate-200 rounded-xl">
                  <Activity className="w-3.5 h-3.5 text-blue-600" />
                  <span className="truncate">{Math.round(prod.ram)}GB RAM</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500">Benchmark: {prod.score}/100</span>
              <button
                onClick={() => onCompare([prod])}
                className="text-xs font-black text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
              >
                <Scale className="w-3.5 h-3.5" /> Spec Matrix
              </button>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
