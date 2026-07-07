"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";
import {
  listCollections,
  createCollection,
  deleteCollection,
  listCollectionDocuments,
  uploadCollectionDocument,
  deleteCollectionDocument,
  listOfficialBenchmarks,
  prepareOfficialBenchmark,
  type Collection,
  type CollectionDocument,
  type OfficialBenchmark,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Plus, Trash2, Upload, FileText, Loader2, Download, Award } from "lucide-react";

interface CollectionManagerProps {
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export default function CollectionManager({ selectedId, onSelect }: CollectionManagerProps) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [official, setOfficial] = useState<OfficialBenchmark[]>([]);
  const [preparing, setPreparing] = useState<Set<string>>(new Set());
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [documents, setDocuments] = useState<CollectionDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const refreshCollections = useCallback(() => {
    listCollections()
      .then(setCollections)
      .catch((e) => toast.error("Failed to load collections", { description: String(e) }));
  }, []);

  const refreshOfficial = useCallback(() => {
    listOfficialBenchmarks()
      .then(setOfficial)
      .catch((e) => toast.error("Failed to load official benchmarks", { description: String(e) }));
  }, []);

  const isOfficialSelected = official.some((b) => b.collection_id && b.collection_id === selectedId);

  const handlePrepare = async (kind: string) => {
    setPreparing((prev) => new Set(prev).add(kind));
    try {
      await prepareOfficialBenchmark(kind);
      toast.success("Download & seeding started", {
        description: "Full datasets are large; this runs in the background.",
      });
    } catch (e) {
      toast.error("Failed to start preparation", { description: String(e) });
      setPreparing((prev) => {
        const n = new Set(prev);
        n.delete(kind);
        return n;
      });
    }
  };

  const refreshDocuments = useCallback((id: string) => {
    listCollectionDocuments(id)
      .then(setDocuments)
      .catch((e) => toast.error("Failed to load documents", { description: String(e) }));
  }, []);

  useEffect(() => {
    refreshCollections();
    refreshOfficial();
  }, [refreshCollections, refreshOfficial]);

  // Poll official benchmark status while a preparation is in flight, and clear
  // the "preparing" flag once the dataset shows up as downloaded + seeded.
  useEffect(() => {
    if (preparing.size === 0) return;
    const timer = setInterval(() => {
      listOfficialBenchmarks()
        .then((list) => {
          setOfficial(list);
          setPreparing((prev) => {
            const n = new Set(prev);
            for (const b of list) {
              if (b.downloaded && b.document_count > 0) n.delete(b.kind);
            }
            return n;
          });
          refreshCollections();
        })
        .catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [preparing, refreshCollections]);

  useEffect(() => {
    if (selectedId) refreshDocuments(selectedId);
  }, [selectedId, refreshDocuments]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const c = await createCollection(newName.trim());
      setNewName("");
      refreshCollections();
      onSelect(c.id);
    } catch (e) {
      toast.error("Failed to create collection", { description: String(e) });
    }
    setCreating(false);
  };

  const handleDeleteCollection = async (id: string) => {
    if (!confirm("Delete this collection and all its documents?")) return;
    try {
      await deleteCollection(id);
      if (selectedId === id) onSelect(null);
      refreshCollections();
    } catch (e) {
      toast.error("Failed to delete collection", { description: String(e) });
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || !selectedId) return;
    setUploading(true);
    let ok = 0;
    for (const file of Array.from(files)) {
      try {
        await uploadCollectionDocument(selectedId, file);
        ok++;
      } catch (e) {
        toast.error(`Upload failed: ${file.name}`, { description: String(e) });
      }
    }
    if (ok > 0) {
      toast.success(`Uploaded ${ok} document(s)`);
      refreshDocuments(selectedId);
      refreshCollections();
    }
    setUploading(false);
    if (fileInput.current) fileInput.current.value = "";
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!selectedId) return;
    try {
      await deleteCollectionDocument(selectedId, docId);
      refreshDocuments(selectedId);
      refreshCollections();
    } catch (e) {
      toast.error("Failed to delete document", { description: String(e) });
    }
  };

  const userCollections = collections.filter((c) => c.kind === "user");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Collections</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Official benchmarks (ground-truth scored) */}
        <div className="space-y-1">
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Award className="h-3.5 w-3.5" /> Official benchmarks
          </p>
          {official.map((b) => {
            const isPreparing = preparing.has(b.kind);
            const ready = b.downloaded && b.document_count > 0 && b.collection_id;
            return (
              <div
                key={b.kind}
                className={cn(
                  "flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors",
                  ready && "cursor-pointer",
                  selectedId === b.collection_id
                    ? "bg-primary text-primary-foreground"
                    : ready
                      ? "hover:bg-muted"
                      : "opacity-90",
                )}
                onClick={() => ready && b.collection_id && onSelect(b.collection_id)}
              >
                <span className="truncate">
                  {b.name}
                  {ready && (
                    <span
                      className={cn(
                        "ml-2 text-xs",
                        selectedId === b.collection_id
                          ? "text-primary-foreground/70"
                          : "text-muted-foreground",
                      )}
                    >
                      {b.document_count} docs
                    </span>
                  )}
                </span>
                {ready ? (
                  <Badge variant="secondary" className="text-[10px]">
                    scored
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 gap-1.5 text-xs"
                    disabled={isPreparing}
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePrepare(b.kind);
                    }}
                  >
                    {isPreparing ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5" />
                    )}
                    {isPreparing ? "Preparing…" : "Download"}
                  </Button>
                )}
              </div>
            );
          })}
        </div>

        <div className="flex gap-2 border-t border-border pt-4">
          <Input
            placeholder="New collection name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <Button onClick={handleCreate} disabled={creating || !newName.trim()} size="icon">
            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          </Button>
        </div>

        <div className="space-y-1">
          {userCollections.length === 0 && (
            <p className="text-sm text-muted-foreground py-2">No collections yet.</p>
          )}
          {userCollections.map((c) => (
            <div
              key={c.id}
              className={cn(
                "group flex items-center justify-between rounded-md px-3 py-2 text-sm cursor-pointer transition-colors",
                selectedId === c.id ? "bg-primary text-primary-foreground" : "hover:bg-muted",
              )}
              onClick={() => onSelect(c.id)}
            >
              <span className="truncate">
                {c.name}
                <span
                  className={cn(
                    "ml-2 text-xs",
                    selectedId === c.id ? "text-primary-foreground/70" : "text-muted-foreground",
                  )}
                >
                  {c.document_count} docs
                </span>
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteCollection(c.id);
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>

        {selectedId && isOfficialSelected && (
          <p className="border-t border-border pt-4 text-xs text-muted-foreground">
            Official benchmark — documents and ground truth are fixed. Select models and run
            to score against the official metrics.
          </p>
        )}

        {selectedId && !isOfficialSelected && (
          <div className="space-y-2 border-t border-border pt-4">
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.pdf,.tiff,.bmp"
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
            >
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Upload documents
            </Button>

            <div className="space-y-1">
              {documents.map((d) => (
                <div
                  key={d.id}
                  className="group flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                >
                  <span className="flex items-center gap-2 truncate">
                    <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{d.original_name}</span>
                  </span>
                  <button
                    onClick={() => handleDeleteDocument(d.id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {documents.length === 0 && (
                <p className="text-xs text-muted-foreground py-1">No documents in this collection.</p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
