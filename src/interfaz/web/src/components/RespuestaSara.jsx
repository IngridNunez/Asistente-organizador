export default function RespuestaSara({ mensaje, estado }) {
  const esError = estado === 'error';
  const esCancelado = estado === 'cancelado';

  return (
    <div
      className={`flex min-h-[104px] w-full max-w-2xl items-start gap-4 rounded-2xl border p-5 text-left shadow-sm transition-all duration-300 md:min-h-[112px] md:rounded-3xl md:p-6 lg:p-7 ${
        esError
          ? 'border-rose-200 bg-rose-50/90 text-rose-900 shadow-rose-100'
          : esCancelado
            ? 'border-slate-200 bg-slate-100/90 text-slate-800'
            : 'border-emerald-100 bg-white/95 text-sara-text shadow-emerald-950/5'
      }`}
      role="status"
      aria-live="polite"
      aria-label="Respuesta de S.A.R.A."
    >
      <div
        className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl text-base md:h-12 md:w-12 md:text-lg ${
          esError
            ? 'bg-rose-100 text-rose-600'
            : esCancelado
              ? 'bg-slate-200 text-slate-600'
              : 'bg-sara-acento/15 text-sara-acento'
        }`}
        aria-hidden="true"
      >
        <i
          className={`fa-solid ${
            esError
              ? 'fa-triangle-exclamation'
              : esCancelado
                ? 'fa-ban'
                : 'fa-sparkles'
          }`}
        />
      </div>
      <div className="min-w-0 flex-1">
        <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-sara-text/50 md:text-sm">
          {esError ? 'Mensaje del sistema' : 'S.A.R.A.'}
        </p>
        <p className="break-words text-base font-medium leading-relaxed md:text-lg lg:text-xl">
          {mensaje || '...'}
        </p>
      </div>
    </div>
  );
}
