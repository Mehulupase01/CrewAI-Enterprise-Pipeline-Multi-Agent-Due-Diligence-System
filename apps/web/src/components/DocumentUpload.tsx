"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";

import { uploadDocument } from "@/lib/api-client";

import styles from "./interactive.module.css";

const DOCUMENT_KINDS = [
  "financial_statements",
  "audited_financials",
  "board_minutes",
  "legal_agreement",
  "regulatory_filing",
  "tax_return",
  "commercial_contract",
  "management_presentation",
  "other",
];

const SOURCE_KINDS = [
  "uploaded_dataroom",
  "management_response",
  "public_filing",
  "third_party_report",
];

const WORKSTREAM_DOMAINS = [
  "financial_qoe",
  "legal_corporate",
  "tax",
  "regulatory",
  "commercial",
  "cyber_privacy",
];

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

type UploadResult = {
  fileName: string;
  evidenceCreated: number;
  chunksCreated: number;
};

export default function DocumentUpload({ caseId }: { caseId: string }) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documentKind, setDocumentKind] = useState(DOCUMENT_KINDS[0]);
  const [sourceKind, setSourceKind] = useState(SOURCE_KINDS[0]);
  const [workstream, setWorkstream] = useState(WORKSTREAM_DOMAINS[0]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<UploadResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      setUploading(true);
      setError(null);
      const fileArray = Array.from(files);
      for (const file of fileArray) {
        try {
          const result = await uploadDocument(
            caseId,
            file,
            documentKind,
            sourceKind,
            workstream,
          );
          setResults((prev) => [
            ...prev,
            {
              fileName: file.name,
              evidenceCreated: result.evidence_created,
              chunksCreated: result.chunks_created,
            },
          ]);
        } catch (err) {
          setError(
            err instanceof Error ? err.message : `Failed to upload ${file.name}`,
          );
        }
      }
      setUploading(false);
      router.refresh();
    },
    [caseId, documentKind, sourceKind, workstream, router],
  );

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(true);
  }

  function handleDragLeave() {
    setDragActive(false);
  }

  return (
    <div>
      <div className={styles.fieldGroup}>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>Document Kind</label>
          <select
            className={styles.select}
            value={documentKind}
            onChange={(e) => setDocumentKind(e.target.value)}
          >
            {DOCUMENT_KINDS.map((k) => (
              <option key={k} value={k}>
                {labelize(k)}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>Source</label>
          <select
            className={styles.select}
            value={sourceKind}
            onChange={(e) => setSourceKind(e.target.value)}
          >
            {SOURCE_KINDS.map((k) => (
              <option key={k} value={k}>
                {labelize(k)}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>Workstream</label>
          <select
            className={styles.select}
            value={workstream}
            onChange={(e) => setWorkstream(e.target.value)}
          >
            {WORKSTREAM_DOMAINS.map((k) => (
              <option key={k} value={k}>
                {labelize(k)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div
        className={`${styles.dropZone} ${dragActive ? styles.dropZoneActive : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFiles(e.target.files);
            }
          }}
        />
        <span className={styles.dropZoneLabel}>
          {uploading ? "Uploading..." : "Drop files here or click to browse"}
        </span>
        <span className={styles.dropZoneHint}>
          PDF, DOCX, XLSX, CSV, JSON, TXT
        </span>
      </div>

      {error && <p className={styles.errorMsg}>{error}</p>}

      {results.length > 0 && (
        <div className={styles.fileList}>
          {results.map((r, i) => (
            <div key={i} className={styles.fileItem}>
              <span className={styles.fileName}>{r.fileName}</span>
              <span className={styles.successMsg}>
                {r.evidenceCreated} evidence, {r.chunksCreated} chunks
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
