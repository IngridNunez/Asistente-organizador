const aparienciasPorEstado = {
  reposo: {
    boton: 'bg-sara-text text-white shadow-xl shadow-slate-900/10 hover:bg-[#1e1e27]',
    etiqueta: 'Presiona para hablar con S.A.R.A.',
    icono: 'fa-microphone',
  },
  escuchando: {
    boton: 'animate-pulse-listening bg-sara-acento text-white hover:bg-sara-acento-hover',
    etiqueta: 'Presiona para enviar tu mensaje',
    icono: 'fa-stop',
  },
  pensando: {
    boton: 'cursor-wait bg-indigo-500 text-white',
    etiqueta: 'S.A.R.A. está procesando tu mensaje',
    icono: 'fa-circle-notch animate-spin',
  },
  preguntando: {
    boton: 'bg-amber-500 text-white hover:bg-amber-600',
    etiqueta: 'Presiona para responder por voz',
    icono: 'fa-microphone',
  },
  hablando: {
    boton: 'animate-pulse-speaking bg-sky-500 text-white',
    etiqueta: 'S.A.R.A. está respondiendo',
    icono: 'fa-volume-high',
  },
  error: {
    boton: 'bg-rose-500 text-white hover:bg-rose-600',
    etiqueta: 'Presiona para intentar nuevamente',
    icono: 'fa-rotate-right',
  },
  cancelado: {
    boton: 'bg-slate-400 text-white hover:bg-slate-500',
    etiqueta: 'Presiona para volver a intentar',
    icono: 'fa-microphone',
  },
};

export default function BotonMicrofono({ estado, onClick, deshabilitado = false }) {
  const apariencia = aparienciasPorEstado[estado] ?? aparienciasPorEstado.reposo;
  const bloqueado =
    deshabilitado || estado === 'pensando' || estado === 'hablando';

  return (
    <div className="flex flex-col items-center">
      <button
        type="button"
        onClick={onClick}
        disabled={bloqueado}
        aria-label={apariencia.etiqueta}
        className={`flex h-20 w-20 items-center justify-center rounded-full transition-all duration-300 active:scale-95 focus:outline-none focus-visible:ring-4 focus-visible:ring-sara-acento focus-visible:ring-offset-4 focus-visible:ring-offset-sara-superficie disabled:cursor-not-allowed sm:h-24 sm:w-24 lg:h-28 lg:w-28 ${apariencia.boton}`}
      >
        <i className={`fa-solid ${apariencia.icono} text-3xl sm:text-4xl`} aria-hidden="true" />
      </button>
      <span className="mt-3 text-xs font-semibold tracking-wide text-sara-text/60 md:mt-4 md:text-sm">
        {apariencia.etiqueta}
      </span>
    </div>
  );
}
