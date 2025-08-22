import type { ReactNode } from "react"

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
}

const Modal = ({ isOpen, onClose, children }: ModalProps) => {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[1000] bg-black/40 flex justify-center items-center"
      onClick={onClose}
    >
      <div
        className="relative bg-white p-8 rounded-lg w-full max-w-[800px] max-h-[90vh] min-h-[500px] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="absolute top-2.5 right-3.5 text-2xl bg-none border-none cursor-pointer"
          onClick={onClose}
        >
          &times;
        </button>
        {children}
      </div>
    </div>
  )
}

export default Modal