import React, { useState, useEffect } from 'react';
import { QRCodeSVG, QRCodeCanvas } from 'qrcode.react';
import {
  X,
  Download,
  Copy,
  Check,
  ExternalLink,
  QrCode,
  AlertTriangle,
  Palette,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';

interface QrCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  shortCode: string;
  destinationUrl: string;
  title?: string | null;
}

const COLOR_PRESETS = [
  { name: 'Classic', fg: '#000000', bg: '#FFFFFF' },
  { name: 'Brand Indigo', fg: '#4F46E5', bg: '#FFFFFF' },
  { name: 'Dark Slate', fg: '#FFFFFF', bg: '#0F172A' },
  { name: 'Emerald', fg: '#059669', bg: '#FFFFFF' },
  { name: 'Midnight Violet', fg: '#818CF8', bg: '#1E1B4B' },
];

/**
 * Calculate relative luminance and contrast ratio between two hex colors.
 */
function getContrastRatio(hex1: string, hex2: string): number {
  const getLuminance = (hex: string): number => {
    let cleanHex = hex.replace('#', '');
    if (cleanHex.length === 3) {
      cleanHex = cleanHex
        .split('')
        .map((c) => c + c)
        .join('');
    }
    if (cleanHex.length !== 6) return 0.5;

    const r = parseInt(cleanHex.substring(0, 2), 16) / 255;
    const g = parseInt(cleanHex.substring(2, 4), 16) / 255;
    const b = parseInt(cleanHex.substring(4, 6), 16) / 255;

    const transform = (val: number) =>
      val <= 0.03928 ? val / 12.92 : Math.pow((val + 0.055) / 1.055, 2.4);

    return 0.2126 * transform(r) + 0.7152 * transform(g) + 0.0722 * transform(b);
  };

  const l1 = getLuminance(hex1);
  const l2 = getLuminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function isValidHex(hex: string): boolean {
  return /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(hex);
}

export const QrCodeModal: React.FC<QrCodeModalProps> = ({
  isOpen,
  onClose,
  shortCode,
  destinationUrl,
  title,
}) => {
  const [fgColor, setFgColor] = useState('#000000');
  const [bgColor, setBgColor] = useState('#FFFFFF');
  const [fgInput, setFgInput] = useState('#000000');
  const [bgInput, setBgInput] = useState('#FFFFFF');
  const [copied, setCopied] = useState(false);

  // The QR code strictly encodes the public short URL to guarantee telemetry recording
  const publicShortUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/r/${shortCode}`
    : `/r/${shortCode}`;

  // Keyboard navigation: Escape key closes modal
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Handle Foreground Color Change
  const handleFgChange = (newHex: string) => {
    setFgInput(newHex);
    if (isValidHex(newHex)) {
      setFgColor(newHex);
    }
  };

  // Handle Background Color Change
  const handleBgChange = (newHex: string) => {
    setBgInput(newHex);
    if (isValidHex(newHex)) {
      setBgColor(newHex);
    }
  };

  // Apply Preset
  const applyPreset = (fg: string, bg: string) => {
    setFgColor(fg);
    setFgInput(fg);
    setBgColor(bg);
    setBgInput(bg);
  };

  // Contrast validation
  const contrastRatio = getContrastRatio(fgColor, bgColor);
  const isLowContrast = contrastRatio < 2.5;

  // Copy Short URL Helper
  const handleCopyUrl = async () => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(publicShortUrl);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = publicShortUrl;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      toast.success('Short link copied!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy link');
    }
  };

  // PNG Download: High-resolution raster export from canvas
  const handleDownloadPng = () => {
    const canvas = document.getElementById('qr-canvas-download') as HTMLCanvasElement | null;
    if (!canvas) {
      toast.error('Could not generate PNG image');
      return;
    }

    try {
      const dataUrl = canvas.toDataURL('image/png');
      const downloadLink = document.createElement('a');
      downloadLink.href = dataUrl;
      downloadLink.download = `spheresphere-${shortCode}.png`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      toast.success('PNG QR code downloaded!');
    } catch {
      toast.error('Failed to download PNG');
    }
  };

  // SVG Download: Vector XML export for crisp scaling and print
  const handleDownloadSvg = () => {
    const svgElement = document.getElementById('qr-svg-preview');
    if (!svgElement) {
      toast.error('Could not generate SVG vector');
      return;
    }

    try {
      const serializer = new XMLSerializer();
      const svgString = serializer.serializeToString(svgElement);
      // Ensure clean, standard-compliant standalone XML declaration
      const fullSvgXml = `<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n${svgString}`;

      const svgBlob = new Blob([fullSvgXml], { type: 'image/svg+xml;charset=utf-8' });
      const blobUrl = URL.createObjectURL(svgBlob);

      const downloadLink = document.createElement('a');
      downloadLink.href = blobUrl;
      downloadLink.download = `spheresphere-${shortCode}.svg`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      URL.revokeObjectURL(blobUrl);

      toast.success('SVG vector QR code downloaded!');
    } catch {
      toast.error('Failed to download SVG');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="qr-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="relative w-full max-w-lg rounded-3xl bg-slate-900 border border-white/15 p-6 sm:p-8 shadow-2xl space-y-6 text-left my-8">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <QrCode className="w-5 h-5" />
            </div>
            <div>
              <h2 id="qr-modal-title" className="text-lg font-bold text-white">
                QR Code Generator
              </h2>
              <p className="text-xs text-gray-400">
                Customizable scan-to-redirect QR code
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            aria-label="Close QR Code dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Link Metadata Summary */}
        <div className="rounded-2xl bg-white/5 border border-white/10 p-3.5 space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-indigo-300">/r/{shortCode}</span>
              {title && <span className="text-gray-300 font-medium truncate max-w-[180px]">({title})</span>}
            </div>
            <button
              onClick={handleCopyUrl}
              className="inline-flex items-center gap-1 text-[11px] text-indigo-300 hover:text-white font-semibold cursor-pointer"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy URL'}</span>
            </button>
          </div>
          <div className="flex items-center gap-1.5 text-gray-400 truncate">
            <ExternalLink className="w-3 h-3 flex-shrink-0 text-gray-500" />
            <span className="truncate">{destinationUrl}</span>
          </div>
        </div>

        {/* QR Code Preview Box */}
        <div className="flex flex-col items-center justify-center space-y-3">
          <div
            className="p-5 rounded-2xl shadow-xl transition-all duration-200 border border-white/10 flex items-center justify-center"
            style={{ backgroundColor: bgColor }}
          >
            {/* Visible SVG Preview */}
            <QRCodeSVG
              id="qr-svg-preview"
              value={publicShortUrl}
              size={200}
              fgColor={fgColor}
              bgColor={bgColor}
              level="H"
              includeMargin={false}
            />
            {/* Hidden High-Resolution 1024px Canvas for Clean PNG Export */}
            <div style={{ display: 'none' }}>
              <QRCodeCanvas
                id="qr-canvas-download"
                value={publicShortUrl}
                size={1024}
                fgColor={fgColor}
                bgColor={bgColor}
                level="H"
                includeMargin
              />
            </div>
          </div>

          <p className="text-[11px] text-gray-400 text-center max-w-xs">
            Encodes <span className="font-mono text-indigo-300">{publicShortUrl}</span> for real-time 302 redirect & telemetry tracking.
          </p>
        </div>

        {/* Contrast Warning Alert */}
        {isLowContrast && (
          <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-3 flex items-start gap-2.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p>
              <strong className="font-semibold">Low Contrast Warning:</strong> The chosen foreground and background colors are very similar (contrast {contrastRatio.toFixed(1)}:1). Smartphone camera scanners may have difficulty reading this code.
            </p>
          </div>
        )}

        {/* Color Customization Controls */}
        <div className="space-y-4 pt-2 border-t border-white/10">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
              <Palette className="w-3.5 h-3.5 text-indigo-400" />
              <span>Customize Colors</span>
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Foreground Color */}
            <div className="space-y-1.5">
              <label htmlFor="fg-color-picker" className="block text-xs font-semibold text-gray-300">
                Pattern Color
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="fg-color-picker"
                  type="color"
                  value={fgColor}
                  onChange={(e) => handleFgChange(e.target.value)}
                  className="w-9 h-9 rounded-xl border border-white/15 bg-transparent cursor-pointer p-0.5"
                  aria-label="Select QR pattern foreground color"
                />
                <input
                  type="text"
                  value={fgInput}
                  onChange={(e) => handleFgChange(e.target.value)}
                  maxLength={7}
                  placeholder="#000000"
                  className="w-full px-3 py-1.5 rounded-xl bg-white/5 border border-white/15 text-white font-mono text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase"
                  aria-label="QR pattern foreground hex code"
                />
              </div>
            </div>

            {/* Background Color */}
            <div className="space-y-1.5">
              <label htmlFor="bg-color-picker" className="block text-xs font-semibold text-gray-300">
                Background Color
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="bg-color-picker"
                  type="color"
                  value={bgColor}
                  onChange={(e) => handleBgChange(e.target.value)}
                  className="w-9 h-9 rounded-xl border border-white/15 bg-transparent cursor-pointer p-0.5"
                  aria-label="Select QR background color"
                />
                <input
                  type="text"
                  value={bgInput}
                  onChange={(e) => handleBgChange(e.target.value)}
                  maxLength={7}
                  placeholder="#FFFFFF"
                  className="w-full px-3 py-1.5 rounded-xl bg-white/5 border border-white/15 text-white font-mono text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase"
                  aria-label="QR background hex code"
                />
              </div>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-gray-400 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              <span>Color Themes</span>
            </span>
            <div className="flex flex-wrap gap-2">
              {COLOR_PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => applyPreset(preset.fg, preset.bg)}
                  className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-medium text-gray-300 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full border border-white/20"
                    style={{ backgroundColor: preset.fg }}
                  />
                  <span>{preset.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Action Buttons: Downloads & Close */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-white/10">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
          >
            Close
          </button>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={handleDownloadPng}
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download PNG</span>
            </button>
            <button
              type="button"
              onClick={handleDownloadSvg}
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/15 text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-indigo-400" />
              <span>Download SVG</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
