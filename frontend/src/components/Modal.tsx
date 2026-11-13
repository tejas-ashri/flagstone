import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}

// Native <dialog>: focus trapping, Esc to close and the backdrop come free.
export function Modal({ open, title, onClose, children, footer }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={e => {
        e.preventDefault();
        onClose();
      }}
      onClick={e => {
        if (e.target === ref.current) onClose(); // click on the backdrop
      }}
    >
      {open && (
        <div className="modal-body">
          <h3 id="modal-title">{title}</h3>
          {children}
          {footer && <div className="modal-footer">{footer}</div>}
        </div>
      )}
    </dialog>
  );
}

interface ConfirmProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  // When set, the confirm button stays disabled until this text is typed.
  requireText?: string;
  typedText?: string;
  onTypedTextChange?: (text: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog(props: ConfirmProps) {
  const blocked = props.requireText !== undefined && props.typedText !== props.requireText;
  return (
    <Modal
      open={props.open}
      title={props.title}
      onClose={props.onCancel}
      footer={
        <>
          <button type="button" className="btn" onClick={props.onCancel}>Cancel</button>
          <button
            type="button"
            className={`btn ${props.danger ? "danger-solid" : "primary"}`}
            disabled={props.busy || blocked}
            onClick={props.onConfirm}
            autoFocus={props.requireText === undefined}
          >
            {props.busy ? "Working…" : props.confirmLabel}
          </button>
        </>
      }
    >
      <div className="muted">{props.message}</div>
      {props.requireText !== undefined && (
        <label className="field">
          <span>Type <code>{props.requireText}</code> to confirm</span>
          <input
            autoFocus
            value={props.typedText ?? ""}
            onChange={e => props.onTypedTextChange?.(e.target.value)}
          />
        </label>
      )}
    </Modal>
  );
}
