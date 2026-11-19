export default function BotonesError({ onReintentar }) {
  return (
    <div className="mt-3 flex w-full max-w-sm items-center justify-center">
      <button
        type="button"
        onClick={onReintentar}
        className="flex w-full items-center justify-center gap-3 rounded-xl bg-sara-acento px-8 py-3.5 text-sm font-bold text-white shadow-lg shadow-sara-acento/30 transition-all hover:bg-sara-acento-hover focus:outline-none focus-visible:ring-4 focus-visible:ring-sara-acento focus-visible:ring-offset-2 active:scale-95 md:rounded-2xl md:py-4 md:text-base"
      >
        <i className="fa-solid fa-rotate-right text-base md:text-lg" aria-hidden="true" />
        <span>Intentar de nuevo</span>
      </button>
    </div>
  );
}
