import { useEffect, useState } from 'react';
import saraReposando from '../assets/sara/sara_reposando.png';
import saraEscuchando from '../assets/sara/sara_escuchando.png';
import saraPensando from '../assets/sara/sara_pensando.png';
import saraPreguntando from '../assets/sara/sara_preguntando.png';
import saraHablando from '../assets/sara/sara_hablando.png';
import saraError from '../assets/sara/sara_error.png';
import saraCancelado from '../assets/sara/sara_cancelado.png';

const imagenesPorEstado = {
  reposo: saraReposando,
  escuchando: saraEscuchando,
  pensando: saraPensando,
  preguntando: saraPreguntando,
  hablando: saraHablando,
  error: saraError,
  cancelado: saraCancelado,
};

const etiquetasPorEstado = {
  reposo: 'Modo reposo',
  escuchando: 'Escuchando',
  pensando: 'Pensando',
  preguntando: 'Preguntando',
  hablando: 'Hablando',
  error: 'Error',
  cancelado: 'Cancelado',
};

const coloresPorEstado = {
  reposo: 'bg-emerald-500',
  escuchando: 'bg-sara-acento',
  pensando: 'bg-indigo-500',
  preguntando: 'bg-amber-500',
  hablando: 'bg-sky-500',
  error: 'bg-rose-500',
  cancelado: 'bg-slate-400',
};

const arosPorEstado = {
  reposo: 'ring-4 ring-emerald-200/90 ring-offset-4',
  escuchando:
    'ring-4 ring-sara-acento ring-offset-4 shadow-xl shadow-sara-acento/30',
  pensando:
    'ring-4 ring-indigo-400 ring-offset-4 shadow-xl shadow-indigo-400/25',
  preguntando:
    'ring-4 ring-amber-400 ring-offset-4 shadow-xl shadow-amber-400/25',
  hablando:
    'ring-4 ring-sky-400 ring-offset-4 shadow-xl shadow-sky-400/25',
  error: 'ring-4 ring-rose-500 ring-offset-4 shadow-xl shadow-rose-500/30',
  cancelado: 'ring-4 ring-slate-400 ring-offset-4 shadow-md',
};

const iconosPorEstado = {
  reposo: 'fa-moon',
  escuchando: 'fa-wave-square',
  pensando: 'fa-circle-notch',
  preguntando: 'fa-question',
  hablando: 'fa-volume-high',
  error: 'fa-exclamation',
  cancelado: 'fa-xmark',
};

export default function Avatar({ estado }) {
  const [imagenFallida, setImagenFallida] = useState(false);
  const estadoConocido = imagenesPorEstado[estado] ? estado : 'reposo';

  useEffect(() => {
    setImagenFallida(false);
  }, [estadoConocido]);

  return (
    <div className="flex flex-col items-center">
      <div
        className={`relative flex h-52 w-52 items-center justify-center overflow-hidden rounded-full bg-gradient-to-b from-[#f3faf7] to-[#e4f3ed] transition-all duration-300 sm:h-60 sm:w-60 md:h-64 md:w-64 lg:h-72 lg:w-72 ${arosPorEstado[estadoConocido]}`}
      >
        {imagenFallida ? (
          <div
            className="flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-sara-superficie to-sara-acento/20 text-sara-acento"
            role="img"
            aria-label="Avatar de S.A.R.A."
          >
            <span className="text-7xl font-black">S</span>
            <span className="text-sm font-extrabold uppercase tracking-widest">
              S.A.R.A.
            </span>
          </div>
        ) : (
          <img
            src={imagenesPorEstado[estadoConocido]}
            alt={`Avatar de S.A.R.A. en estado ${etiquetasPorEstado[estadoConocido]}`}
            className="h-full w-full object-cover object-top transition-transform duration-300 hover:scale-105"
            onError={() => setImagenFallida(true)}
          />
        )}
        <div
          className={`absolute bottom-3 right-4 flex h-8 w-8 items-center justify-center rounded-full border-[3px] border-white text-xs text-white shadow-md sm:bottom-4 sm:right-6 ${coloresPorEstado[estadoConocido]}`}
          aria-hidden="true"
        >
          <i
            className={`fa-solid ${iconosPorEstado[estadoConocido]} ${
              estadoConocido === 'pensando' ? 'animate-spin' : ''
            } ${estadoConocido === 'escuchando' || estadoConocido === 'hablando' ? 'animate-pulse' : ''}`}
          />
        </div>
      </div>
      <div className="mt-5 flex items-center gap-2.5 rounded-full border border-slate-200/50 bg-slate-100/70 px-4 py-1.5 md:mt-6">
        <span
          className={`h-3 w-3 rounded-full ${coloresPorEstado[estadoConocido]} ${
            estadoConocido === 'escuchando' ? 'animate-ping' : ''
          }`}
          aria-hidden="true"
        />
        <span className="text-xs font-extrabold uppercase tracking-widest text-sara-text/85 md:text-sm">
          {etiquetasPorEstado[estadoConocido]}
        </span>
      </div>
    </div>
  );
}
