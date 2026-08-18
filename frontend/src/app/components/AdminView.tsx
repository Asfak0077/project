"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldAlert,
  Database,
  Upload,
  Plus,
  Trash2,
  Edit2,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Layers,
  ArrowLeft,
  X,
} from "lucide-react";
import {
  getAdminProducts,
  createAdminProduct,
  updateAdminProduct,
  deleteAdminProduct,
  importAdminCSV,
  getAdminAnalytics,
} from "../../services/api";
import { Product } from "../types";

interface AdminViewProps {
  onBack: () => void;
}

export default function AdminView({ onBack }: AdminViewProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  // Modal State for Add / Edit
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState({
    brand: "",
    name: "",
    price: 50000,
    cpu: "Intel Core i5",
    ram: 16,
    storage: "512 GB SSD",
    gpu: "Integrated",
    score: 85,
  });

  useEffect(() => {
    loadAdminData();
  }, [search]);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [prodsData, analyticsData] = await Promise.all([
        getAdminProducts({ search: search || undefined, limit: 30 }),
        getAdminAnalytics().catch(() => null),
      ]);
      setProducts(prodsData.items || []);
      setAnalytics(analyticsData);
    } catch (err) {
      console.error("Admin data loading failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCSVImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setIsImporting(true);
    setImportResult(null);
    try {
      const res = await importAdminCSV(file);
      setImportResult(res);
      loadAdminData();
    } catch (err: any) {
      alert("CSV Import failed: " + (err.message || "Unknown error"));
    } finally {
      setIsImporting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Are you sure you want to delete product '${id}'?`)) return;
    try {
      await deleteAdminProduct(id);
      setProducts((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert("Failed to delete product.");
    }
  };

  const handleSaveProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingProduct) {
        const updated = await updateAdminProduct(editingProduct.id, formData);
        setProducts((prev) => prev.map((p) => (p.id === editingProduct.id ? updated : p)));
        setEditingProduct(null);
      } else if (isCreating) {
        const created = await createAdminProduct(formData);
        setProducts((prev) => [created, ...prev]);
        setIsCreating(false);
      }
    } catch (err: any) {
      alert("Save failed: " + err.message);
    }
  };

  return (
    <div className="py-8 space-y-8 pb-32">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-blue-600 mb-2 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </button>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            Admin Inventory & CSV Control <ShieldAlert className="w-6 h-6 text-blue-600" />
          </h1>
          <p className="text-slate-500 text-xs font-semibold mt-1">
            Manage live product catalog, re-run idempotent CSV ingestion, and monitor system metrics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black shadow-md flex items-center gap-2 cursor-pointer transition-all">
            {isImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            <span>{isImporting ? "Ingesting..." : "Import Product CSV"}</span>
            <input type="file" accept=".csv" onChange={handleCSVImport} disabled={isImporting} className="hidden" />
          </label>

          <button
            onClick={() => {
              setFormData({
                brand: "Asus",
                name: "New Laptop Model",
                price: 65000,
                cpu: "Intel Core i7",
                ram: 16,
                storage: "512 GB SSD",
                gpu: "NVIDIA RTX 3050",
                score: 90,
              });
              setIsCreating(true);
            }}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-black shadow-md flex items-center gap-2 cursor-pointer transition-all"
          >
            <Plus className="w-4 h-4" /> Add Product
          </button>
        </div>
      </div>

      {/* CSV Import Results Banner */}
      {importResult && (
        <div className="p-5 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs text-emerald-900 space-y-1">
          <div className="font-black flex items-center gap-1.5 text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" /> CSV Ingestion Completed Successfully
          </div>
          <p className="font-semibold">
            Total Processed: <strong>{importResult.total_rows}</strong> | New Products Inserted: <strong>{importResult.new_products}</strong> | Updated: <strong>{importResult.updated_products}</strong>
          </p>
        </div>
      )}

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search catalog by name, brand, or model..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
          />
        </div>
        <button
          onClick={loadAdminData}
          className="p-2.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-700"
          title="Refresh Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Products Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between font-black text-xs text-slate-700 uppercase">
          <span>Catalog Inventory ({products.length})</span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs font-bold text-slate-500">Loading catalog...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50 font-bold text-slate-500">
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Brand & Name</th>
                  <th className="py-3 px-4">Processor</th>
                  <th className="py-3 px-4">RAM</th>
                  <th className="py-3 px-4">Price</th>
                  <th className="py-3 px-4">Score</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {products.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-600">{p.id}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{p.name}</div>
                      <div className="text-[10px] text-slate-400 font-bold">{p.brand}</div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-700">{p.cpu}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">{Math.round(p.ram)}GB</td>
                    <td className="py-3.5 px-4 font-black text-slate-900">₹{p.price.toLocaleString()}</td>
                    <td className="py-3.5 px-4 font-bold text-blue-600">{p.score}/100</td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => {
                          setFormData({
                            brand: p.brand,
                            name: p.name,
                            price: p.price,
                            cpu: p.cpu,
                            ram: p.ram,
                            storage: p.storage,
                            gpu: p.gpu || "Integrated",
                            score: p.score,
                          });
                          setEditingProduct(p);
                        }}
                        className="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg cursor-pointer"
                        title="Edit Product"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(p.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg cursor-pointer"
                        title="Delete Product"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add / Edit Product Modal */}
      <AnimatePresence>
        {(isCreating || editingProduct) && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 max-w-lg w-full shadow-2xl border border-slate-200"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-extrabold text-lg text-slate-900">
                  {editingProduct ? `Edit ${editingProduct.name}` : "Create New Product"}
                </h3>
                <button
                  onClick={() => {
                    setIsCreating(false);
                    setEditingProduct(null);
                  }}
                  className="text-slate-400 hover:text-slate-700"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveProduct} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Brand</label>
                    <input
                      type="text"
                      required
                      value={formData.brand}
                      onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Price (INR)</label>
                    <input
                      type="number"
                      required
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: Number(e.target.value) })}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-900"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-500 block mb-1">Product Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-900"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Processor</label>
                    <input
                      type="text"
                      required
                      value={formData.cpu}
                      onChange={(e) => setFormData({ ...formData, cpu: e.target.value })}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">RAM (GB)</label>
                    <input
                      type="number"
                      required
                      value={formData.ram}
                      onChange={(e) => setFormData({ ...formData, ram: Number(e.target.value) })}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-900"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreating(false);
                      setEditingProduct(null);
                    }}
                    className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-md"
                  >
                    Save Product
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
