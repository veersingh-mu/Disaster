import React from 'react';

export interface LayerState {
  showFloodExtent: boolean;
  depthShading: boolean;
  showSettlements: boolean;
}

interface LayerControlsProps {
  layers: LayerState;
  onToggleLayer: (key: keyof LayerState) => void;
}

export const LayerControls: React.FC<LayerControlsProps> = ({ layers, onToggleLayer }) => {
  return (
    <div className="absolute top-3 right-14 z-10 bg-surface-container-lowest/95 backdrop-blur-md p-3 border border-outline/30 shadow-lg text-xs font-mono flex flex-col gap-2 min-w-[200px]">
      <div className="flex items-center gap-1.5 pb-1.5 border-b border-outline/20 font-bold text-on-surface">
        <span className="material-symbols-outlined text-sm text-primary">layers</span>
        <span>Map Visual Layers</span>
      </div>

      <div className="flex flex-col gap-1.5 text-[11px]">
        <label className="flex items-center gap-2 cursor-pointer hover:text-primary">
          <input
            type="checkbox"
            checked={layers.showFloodExtent}
            onChange={() => onToggleLayer('showFloodExtent')}
            className="accent-primary cursor-pointer"
          />
          <span className="w-2.5 h-2.5 bg-sky-500 inline-block border border-sky-700" />
          <span>Inundation Footprint</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer hover:text-primary">
          <input
            type="checkbox"
            checked={layers.depthShading}
            onChange={() => onToggleLayer('depthShading')}
            className="accent-primary cursor-pointer"
          />
          <span className="w-2.5 h-2.5 bg-gradient-to-r from-sky-400 via-blue-600 to-indigo-900 inline-block border border-outline/30" />
          <span>Depth Graduation</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer hover:text-primary">
          <input
            type="checkbox"
            checked={layers.showSettlements}
            onChange={() => onToggleLayer('showSettlements')}
            className="accent-primary cursor-pointer"
          />
          <span className="w-2.5 h-2.5 bg-rose-600 inline-block border border-white rounded-full" />
          <span>Settlement Risk Pins</span>
        </label>
      </div>

      {/* Mini Legend */}
      <div className="pt-2 border-t border-outline/20 text-[10px] text-secondary flex flex-col gap-1">
        <div className="font-bold text-on-surface text-[10px] uppercase">Severity Legend</div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-rose-600 inline-block" />
          <span>Immediate (&le;30 min)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
          <span>Warning Alert (30–90m)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
          <span>Monitoring (&gt;90 min)</span>
        </div>
      </div>
    </div>
  );
};
