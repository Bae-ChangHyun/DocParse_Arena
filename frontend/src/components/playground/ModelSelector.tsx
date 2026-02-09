"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { OcrModel } from "@/lib/api";

interface ModelSelectorProps {
  models: OcrModel[];
  selectedId: string;
  onSelect: (id: string) => void;
  label: string;
}

export default function ModelSelector({ models, selectedId, onSelect, label }: ModelSelectorProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium">{label}</label>
      <Select value={selectedId} onValueChange={onSelect}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select a model" />
        </SelectTrigger>
        <SelectContent>
          {models.map((model) => (
            <SelectItem key={model.id} value={model.id}>
              <span className="flex items-center gap-2">
                <span>{model.icon}</span>
                <span>{model.display_name}</span>
                <span className="text-xs text-muted-foreground">({model.elo} ELO)</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
