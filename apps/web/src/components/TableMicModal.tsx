import React, { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { Smartphone, X, Copy, Check } from 'lucide-react';

interface TableMicModalProps {
  isOpen: boolean;
  onClose: () => void;
  roomId: string;
}

export const TableMicModal: React.FC<TableMicModalProps> = ({
  isOpen,
  onClose,
  roomId,
}) => {
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);

  // Generate pairing URL
  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173';
  const pairingUrl = `${origin}/?room=${encodeURIComponent(roomId)}&role=mic`;

  useEffect(() => {
    if (isOpen) {
      QRCode.toDataURL(pairingUrl, {
        width: 250,
        margin: 2,
        color: {
          dark: '#0F1117',
          light: '#FBBF24',
        },
      })
        .then((url) => setQrDataUrl(url))
        .catch((err) => console.error('QR generation failed:', err));
    }
  }, [isOpen, pairingUrl]);

  if (!isOpen) return null;

  const copyUrl = () => {
    navigator.clipboard.writeText(pairingUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl relative text-center">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="w-12 h-12 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center mx-auto mb-4">
          <Smartphone className="w-6 h-6" />
        </div>

        <h3 className="text-xl font-bold text-white mb-1">Table-Mic Mode</h3>
        <p className="text-sm text-slate-400 mb-6">
          Place your phone in the center of the table as the microphone while this screen stays visible as the display.
        </p>

        {/* QR Code Container */}
        <div className="flex justify-center mb-6">
          <div className="p-3 bg-amber-400 rounded-2xl shadow-xl inline-block">
            {qrDataUrl ? (
              <img src={qrDataUrl} alt="Table Mic QR Code" className="w-52 h-52 rounded-xl" />
            ) : (
              <div className="w-52 h-52 flex items-center justify-center text-slate-900 font-bold">
                Generating QR...
              </div>
            )}
          </div>
        </div>

        {/* Room Code */}
        <div className="p-3 rounded-xl bg-slate-800 border border-slate-700 mb-4 flex items-center justify-between text-left">
          <div>
            <div className="text-xs text-slate-400">Local Room Code</div>
            <div className="text-lg font-mono font-bold text-amber-400">{roomId}</div>
          </div>
          <button
            onClick={copyUrl}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Link'}</span>
          </button>
        </div>

        <p className="text-xs text-slate-500">
          Works directly over your local home Wi-Fi network without external cloud relays.
        </p>
      </div>
    </div>
  );
};
