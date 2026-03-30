"use client";

import { useState } from "react";

import CreateCaseModal from "./CreateCaseModal";
import styles from "./interactive.module.css";

export default function CreateCaseButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button className={styles.btnPrimary} onClick={() => setOpen(true)}>
        + Create Case
      </button>
      {open && <CreateCaseModal onClose={() => setOpen(false)} />}
    </>
  );
}
