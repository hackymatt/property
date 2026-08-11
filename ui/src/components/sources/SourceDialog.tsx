"use client";
import { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Switch, FormControlLabel, Grid,
  MenuItem, Alert, Box, Typography, IconButton, Divider, Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import { useQuery } from "@tanstack/react-query";
import { sources, domains } from "@/lib/api";
import type {
  ScraperSource, ScraperSourceStage, SourceKind, PropertyType,
} from "@/lib/types";


interface Props {
  open: boolean;
  source: ScraperSource | null;
  onClose: () => void;
  onSave: () => void;
}

const SOURCE_KINDS: { value: SourceKind; label: string }[] = [
  { value: "PORTAL_LISTING", label: "Portal listing" },
  { value: "FILE_REGISTRY", label: "File registry" },
];

const PROPERTY_TYPES: PropertyType[] = ["APARTMENT", "HOUSE", "LAND", "COMMERCIAL"];

/**
 * Convenience presets only — the authoritative list of valid code_ref values
 * is STAGE_REGISTRY in the scraper service repo. The UI cannot read it
 * (services don't call each other's APIs), so code_ref stays free text:
 * a wrong value fails at run time with "Unknown code_ref", visible in the
 * scraper logs and the job's run log.
 */
const STAGE_PRESETS: Record<SourceKind, { stage_name: string; class_name: string }[]> = {
  PORTAL_LISTING: [
    { stage_name: "list_pages", class_name: "ListPagesStage" },
    { stage_name: "list_items", class_name: "ListItemsStage" },
    { stage_name: "get_item", class_name: "GetItemStage" },
  ],
  FILE_REGISTRY: [
    { stage_name: "discover", class_name: "DiscoverStage" },
    { stage_name: "download", class_name: "DownloadStage" },
    { stage_name: "extract", class_name: "ExtractStage" },
    { stage_name: "transform", class_name: "TransformStage" },
    { stage_name: "load", class_name: "LoadStage" },
  ],
};

/** "otodom/sell/apartment" -> "otodom" — matches how STAGE_REGISTRY keys are namespaced. */
const registryPrefix = (sourceName: string) =>
  (sourceName.split("/")[0] || "source").trim();

const DEFAULTS: Partial<ScraperSource> = {
  name: "",
  source_kind: "PORTAL_LISTING",
  property_type: "APARTMENT",
  offer_url_prefix: "",
  config: {},
  is_active: true,
  notes: "",
  stages: [],
};

export default function SourceDialog({ open, source, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<ScraperSource>>(DEFAULTS);
  const [configText, setConfigText] = useState("{}");
  const [configError, setConfigError] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: domainData } = useQuery({
    queryKey: ["domains", "all"],
    queryFn: () => domains.list({ limit: 10000 }).then((r) => r.data.results),
  });
  const domainList = domainData ?? [];

  useEffect(() => {
    setForm(source ?? DEFAULTS);
    setConfigText(JSON.stringify(source?.config ?? {}, null, 2));
    setConfigError("");
    setError("");
  }, [source, open]);

  const set = (k: keyof ScraperSource, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }));

  const handleConfigChange = (text: string) => {
    setConfigText(text);
    try {
      const parsed = text.trim() === "" ? {} : JSON.parse(text);
      set("config", parsed);
      setConfigError("");
    } catch {
      setConfigError("Invalid JSON");
    }
  };

  const stages = form.stages ?? [];
  const isPortal = form.source_kind === "PORTAL_LISTING";

  const setStages = (next: ScraperSourceStage[]) =>
    set("stages", next.map((s, i) => ({ ...s, order: i + 1 })));

  const updateStage = (index: number, key: "stage_name" | "code_ref", value: string) =>
    setStages(stages.map((s, i) => (i === index ? { ...s, [key]: value } : s)));

  const addStage = () =>
    setStages([...stages, { stage_name: "", order: stages.length + 1, code_ref: "" }]);

  const removeStage = (index: number) =>
    setStages(stages.filter((_, i) => i !== index));

  const moveStage = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= stages.length) return;
    const next = [...stages];
    [next[index], next[target]] = [next[target], next[index]];
    setStages(next);
  };

  const applyPreset = () => {
    const kind = (form.source_kind ?? "PORTAL_LISTING") as SourceKind;
    const prefix = registryPrefix(form.name ?? "");
    setStages(
      STAGE_PRESETS[kind].map((s, i) => ({
        stage_name: s.stage_name,
        order: i + 1,
        code_ref: `${prefix}.${s.class_name}`,
      })),
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (configError) {
      setError("Fix the config JSON before saving");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const payload = { ...form, stages: stages.map((s, i) => ({ ...s, order: i + 1 })) };
      if (source?.id) await sources.update(source.id, payload);
      else await sources.create(payload);
      onSave();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: unknown } })?.response?.data;
      setError(JSON.stringify(msg) ?? "Error saving");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>{source ? `Edit Source: ${source.name}` : "Add Scraper Source"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <Grid container spacing={2}>
            <Grid item xs={7}>
              <TextField label="Name" fullWidth required size="small"
                value={form.name ?? ""} onChange={(e) => set("name", e.target.value)}
                placeholder="otodom/sell/apartment"
                helperText="Used verbatim as Job.source" />
            </Grid>
            <Grid item xs={4}>
              <TextField select label="Domain" fullWidth required size="small"
                value={form.domain ?? ""}
                onChange={(e) => set("domain", parseInt(e.target.value))}>
                {domainList.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={1} display="flex" alignItems="flex-start" pt={0.5}>
              <FormControlLabel
                control={<Switch size="small" checked={form.is_active ?? true}
                  onChange={(e) => set("is_active", e.target.checked)} />}
                label={<Typography variant="caption">Active</Typography>}
                labelPlacement="top"
                sx={{ m: 0 }}
              />
            </Grid>

            <Grid item xs={6}>
              <TextField select label="Source kind" fullWidth required size="small"
                value={form.source_kind ?? "PORTAL_LISTING"}
                onChange={(e) => set("source_kind", e.target.value)}
                helperText="Determines the stage vocabulary">
                {SOURCE_KINDS.map((k) => <MenuItem key={k.value} value={k.value}>{k.label}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={6}>
              <TextField select label="Property type" fullWidth required size="small"
                value={form.property_type ?? "APARTMENT"}
                onChange={(e) => set("property_type", e.target.value)}
                helperText="Default for produced records">
                {PROPERTY_TYPES.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <TextField label="Offer URL Prefix" fullWidth size="small"
                value={form.offer_url_prefix ?? ""}
                onChange={(e) => set("offer_url_prefix", e.target.value)}
                disabled={!isPortal}
                helperText={isPortal ? "Base URL for item links" : "Portal listing sources only"} />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Config (JSON)" fullWidth size="small" multiline minRows={3}
                value={configText}
                onChange={(e) => handleConfigChange(e.target.value)}
                error={!!configError}
                helperText={
                  configError ||
                  (isPortal
                    ? "Source-level settings available to every stage. Usually {} for portals."
                    : 'Required for RCN — which GPKG layer this source reads, e.g. {"layer": "transakcje_lokale"}')
                }
                InputProps={{ style: { fontFamily: "monospace", fontSize: 13 } }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField label="Notes" fullWidth size="small" multiline rows={2}
                value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value)} />
            </Grid>
          </Grid>

          <Divider />

          <Box>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
              <Box>
                <Typography variant="subtitle2">Stages</Typography>
                <Typography variant="caption" color="text.secondary">
                  Execution order for this source. Handler code lives in the scraper repo —
                  <code> code_ref</code> only points at a class registered in its STAGE_REGISTRY.
                </Typography>
              </Box>
              <Box display="flex" gap={1} flexShrink={0}>
                <Button size="small" onClick={applyPreset}>Use preset</Button>
                <Button size="small" startIcon={<AddIcon />} onClick={addStage}>Add stage</Button>
              </Box>
            </Box>

            {stages.length === 0 && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                No stages defined — this source will never run. Use “Use preset” for the
                standard {isPortal ? "portal" : "file registry"} pipeline.
              </Alert>
            )}

            {stages.map((stage, index) => (
              <Grid container spacing={1} key={index} alignItems="center" mb={1}>
                <Grid item xs={1}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    {index + 1}
                  </Typography>
                </Grid>
                <Grid item xs={4}>
                  <TextField label="stage_name" fullWidth required size="small"
                    value={stage.stage_name}
                    onChange={(e) => updateStage(index, "stage_name", e.target.value)}
                    placeholder={isPortal ? "list_pages" : "discover"} />
                </Grid>
                <Grid item xs={5}>
                  <TextField label="code_ref" fullWidth required size="small"
                    value={stage.code_ref}
                    onChange={(e) => updateStage(index, "code_ref", e.target.value)}
                    placeholder={isPortal ? "otodom.ListPagesStage" : "rcn.DiscoverStage"} />
                </Grid>
                <Grid item xs={2} display="flex" justifyContent="flex-end">
                  <Tooltip title="Move up">
                    <span>
                      <IconButton size="small" disabled={index === 0}
                        onClick={() => moveStage(index, -1)}>
                        <ArrowUpwardIcon fontSize="inherit" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  <Tooltip title="Move down">
                    <span>
                      <IconButton size="small" disabled={index === stages.length - 1}
                        onClick={() => moveStage(index, 1)}>
                        <ArrowDownwardIcon fontSize="inherit" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  <Tooltip title="Remove">
                    <IconButton size="small" color="error" onClick={() => removeStage(index)}>
                      <DeleteIcon fontSize="inherit" />
                    </IconButton>
                  </Tooltip>
                </Grid>
              </Grid>
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
