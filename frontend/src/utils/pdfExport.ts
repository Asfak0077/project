import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { Product } from "../app/types";
import { CompareResponseData, SpecComparisonRow } from "../services/api";

/**
 * Exports a beautifully styled PDF Comparison Report.
 */
export function exportComparisonToPdf(
  products: Product[],
  overallWinner: Product,
  comparisonData: CompareResponseData | null,
  specRows: SpecComparisonRow[]
) {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;

  // Primary Colors
  const primaryNavy = [15, 23, 42] as const;      // Slate 900
  const accentBlue = [37, 99, 235] as const;       // Blue 600
  const winnerGold = [217, 119, 6] as const;       // Amber 600
  const subtleGray = [100, 116, 139] as const;     // Slate 500
  const lightBg = [248, 250, 252] as const;        // Slate 50

  let currentY = 16;

  // 1. Header Banner
  doc.setFillColor(...primaryNavy);
  doc.roundedRect(margin, currentY, pageWidth - margin * 2, 24, 3, 3, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("VERSUS AI • PRODUCT COMPARISON REPORT", margin + 8, currentY + 10);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor(148, 163, 184); // Slate 400
  doc.text(
    `Generated on: ${new Date().toLocaleString()}  |  Verified Ground Truth: AWS RDS MySQL + RAG Engine`,
    margin + 8,
    currentY + 17
  );

  currentY += 30;

  // 2. Benchmark Winner Showcase Card
  if (overallWinner) {
    const cleanWinnerName = overallWinner.name.toLowerCase().startsWith(overallWinner.brand.toLowerCase() + " ")
      ? overallWinner.name
      : `${overallWinner.brand} ${overallWinner.name}`;

    doc.setFillColor(254, 243, 199); // Amber 100
    doc.setDrawColor(245, 158, 11);  // Amber 500
    doc.roundedRect(margin, currentY, pageWidth - margin * 2, 22, 2.5, 2.5, "FD");

    doc.setTextColor(...winnerGold);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    doc.text(`★ OVERALL BENCHMARK WINNER: ${cleanWinnerName}`, margin + 6, currentY + 7);

    doc.setTextColor(51, 65, 85);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    const summaryText = comparisonData?.winner_summary || "Top ranked device in hardware benchmark efficiency and value.";
    const splitSummary = doc.splitTextToSize(`Score: ${overallWinner.score}/100 | Price: ₹${overallWinner.price.toLocaleString()} | ${summaryText}`, pageWidth - margin * 2 - 12);
    doc.text(splitSummary, margin + 6, currentY + 14);

    currentY += 28;
  }

  // 3. Products Quick Overview Grid Table
  doc.setTextColor(...primaryNavy);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("Compared Devices Overview", margin, currentY);
  currentY += 4;

  const productHeaders = ["#", "Device Model", "Category", "Price", "CPU", "RAM", "Storage", "Score"];
  const productData = products.map((p, idx) => {
    const pName = p.name.toLowerCase().startsWith(p.brand.toLowerCase() + " ") ? p.name : `${p.brand} ${p.name}`;
    return [
      `#${idx + 1}`,
      pName,
      p.category ? p.category.toUpperCase() : "LAPTOP",
      `₹${p.price.toLocaleString()}`,
      p.cpu || "N/A",
      `${Math.round(p.ram)} GB`,
      p.storage || "N/A",
      `${p.score}/100`,
    ];
  });

  autoTable(doc, {
    startY: currentY,
    head: [productHeaders],
    body: productData,
    theme: "striped",
    headStyles: {
      fillColor: [...accentBlue],
      textColor: [255, 255, 255],
      fontStyle: "bold",
      fontSize: 8.5,
      halign: "left",
    },
    bodyStyles: {
      fontSize: 8,
      textColor: [30, 41, 59],
    },
    columnStyles: {
      0: { cellWidth: 10, halign: "center" },
      1: { cellWidth: 45, fontStyle: "bold" },
      3: { fontStyle: "bold", textColor: [37, 99, 235] },
      7: { fontStyle: "bold", halign: "center", textColor: [16, 185, 129] },
    },
    margin: { left: margin, right: margin },
  });

  currentY = (doc as any).lastAutoTable.finalY + 8;

  // 4. Side-by-Side Technical Specification Matrix Table
  doc.setTextColor(...primaryNavy);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("Full Specification Matrix", margin, currentY);
  currentY += 4;

  const matrixHeaders = ["Specification", ...products.map((p) => {
    const shortName = p.name.length > 22 ? p.name.slice(0, 20) + "..." : p.name;
    return `${p.brand}\n${shortName}`;
  })];

  const matrixBody = specRows.map((row) => {
    return [
      row.label,
      ...products.map((p) => {
        const val = row.values && row.values[p.id] ? row.values[p.id] : "N/A";
        return String(val);
      }),
    ];
  });

  autoTable(doc, {
    startY: currentY,
    head: [matrixHeaders],
    body: matrixBody,
    theme: "grid",
    headStyles: {
      fillColor: [...primaryNavy],
      textColor: [255, 255, 255],
      fontStyle: "bold",
      fontSize: 8,
      halign: "center",
    },
    bodyStyles: {
      fontSize: 7.5,
      textColor: [51, 65, 85],
    },
    columnStyles: {
      0: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42], cellWidth: 36 },
    },
    margin: { left: margin, right: margin },
    didDrawPage: (data) => {
      // Footer on every page
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7.5);
      doc.setTextColor(...subtleGray);
      doc.text(
        `VersusAI Product Intelligence Engine • Page ${doc.internal.pages.length - 1}`,
        pageWidth / 2,
        pageHeight - 8,
        { align: "center" }
      );
    },
  });

  // Save the generated PDF
  const filename = `versus-ai-comparison-report-${new Date().toISOString().slice(0, 10)}.pdf`;
  doc.save(filename);
}

/**
 * Exports Chat History to a clean PDF Document.
 */
export function exportChatToPdf(messages: any[]) {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 14;
  let currentY = 16;

  // Header Banner
  doc.setFillColor(15, 23, 42);
  doc.roundedRect(margin, currentY, pageWidth - margin * 2, 22, 3, 3, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text("VERSUS AI • CHAT CONVERSATION TRANSCRIPT", margin + 8, currentY + 10);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  doc.text(`Exported On: ${new Date().toLocaleString()}`, margin + 8, currentY + 16);

  currentY += 28;

  const chatRows = messages.map((m) => {
    const roleStr = m.role === "user" ? "User" : "VersusAI Assistant";
    const timeStr = m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
    const cleanContent = m.content
      ? m.content.replace(/[*#`_]/g, "").replace(/\n{2,}/g, "\n")
      : "";
    return [`${roleStr}\n(${timeStr})`, cleanContent];
  });

  autoTable(doc, {
    startY: currentY,
    head: [["Sender", "Message Content"]],
    body: chatRows,
    theme: "striped",
    headStyles: {
      fillColor: [37, 99, 235],
      textColor: [255, 255, 255],
      fontStyle: "bold",
      fontSize: 9,
    },
    bodyStyles: {
      fontSize: 8.5,
      textColor: [30, 41, 59],
      cellPadding: 4,
    },
    columnStyles: {
      0: { cellWidth: 32, fontStyle: "bold", halign: "center" },
      1: { cellWidth: pageWidth - margin * 2 - 32 },
    },
    margin: { left: margin, right: margin },
  });

  const filename = `versus-ai-chat-${new Date().toISOString().slice(0, 10)}.pdf`;
  doc.save(filename);
}
