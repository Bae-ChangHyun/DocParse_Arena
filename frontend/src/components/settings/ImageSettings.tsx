"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { getImageSettings, updateImageSettings, type ImageSetting } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Loader2 } from "lucide-react";

const MAX_AXIS = 8192;

export default function ImageSettings() {
  const [setting, setSetting] = useState<ImageSetting | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const s = await getImageSettings();
      setSetting(s);
    } catch (e) {
      toast.error("Failed to load image settings", { description: String(e) });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAxisChange = (axis: "max_width" | "max_height", raw: string) => {
    if (!setting) return;
    const n = Number(raw);
    setSetting({ ...setting, [axis]: Number.isFinite(n) ? n : 0 });
  };

  const handleSave = async () => {
    if (!setting) return;
    for (const axis of ["max_width", "max_height"] as const) {
      const v = setting[axis];
      if (!Number.isInteger(v) || v < 1 || v > MAX_AXIS) {
        toast.error(`${axis} must be an integer between 1 and ${MAX_AXIS}`);
        return;
      }
    }
    setSaving(true);
    try {
      const updated = await updateImageSettings(setting);
      setSetting(updated);
      toast.success("Image settings saved");
    } catch (e) {
      toast.error("Failed to save", { description: e instanceof Error ? e.message : String(e) });
    }
    setSaving(false);
  };

  if (loading || !setting) {
    return <div className="text-center py-8 text-muted-foreground">Loading image settings...</div>;
  }

  return (
    <>
      <div className="mb-2">
        <h2 className="text-lg font-semibold">Image Processing</h2>
        <p className="text-sm text-muted-foreground">
          Downscale uploaded images and rendered PDF pages before sending to the model.
          Shrink-only — images smaller than the limit pass through unchanged.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Maximum image size</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Switch
              id="image-enabled"
              checked={setting.enabled}
              onCheckedChange={(v) => setSetting({ ...setting, enabled: v })}
            />
            <Label htmlFor="image-enabled" className="text-sm">
              Enable downscaling
            </Label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Max width (px)</Label>
              <Input
                type="number"
                min={1}
                max={MAX_AXIS}
                value={setting.max_width}
                onChange={(e) => handleAxisChange("max_width", e.target.value)}
                disabled={!setting.enabled}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Max height (px)</Label>
              <Input
                type="number"
                min={1}
                max={MAX_AXIS}
                value={setting.max_height}
                onChange={(e) => handleAxisChange("max_height", e.target.value)}
                disabled={!setting.enabled}
              />
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground">
            Aspect ratio is preserved (LANCZOS thumbnail). Range 1–{MAX_AXIS}px per axis.
          </p>

          <div className="flex justify-end pt-2">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
