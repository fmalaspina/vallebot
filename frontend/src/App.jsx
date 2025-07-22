// src/App.jsx

import './index.css'
import logo from './assets/vallebot_logo.png'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-100 to-blue-200 flex flex-col items-center justify-center text-center px-6 py-12">
      <img
        src={logo}
        alt="Logo de ValleBot"
        className="w-10 h-10 mb-4 animate-bounce drop-shadow-xl"
      />

      <div className="text-blue-900 font-sans text-xl sm:text-3xl font-semibold leading-relaxed tracking-wide max-w-100xl space-y-4">
        <p>Tu asistente inteligente para el seguimiento de turnos y clases.</p>
        <p>Gestiona pagos de alumnos, pacientes o clientes.</p>
        <p>Simple, rápido y desde el corazón del Valle de Calamuchita.</p>
      </div>
    </div>
  )
}

export default App
