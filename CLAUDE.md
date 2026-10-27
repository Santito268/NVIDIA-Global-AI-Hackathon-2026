# CLAUDE.md — Proyecto para el Nebius x NVIDIA Global AI Hackathon 2026

Este archivo le da a Claude Code el contexto y las reglas de este proyecto. Léelo completo antes de escribir código y síguelo en cada sesión.

---

## 1. Contexto del proyecto

- **Qué es:** una aplicación de IA para el **Nebius x NVIDIA Global AI Hackathon 2026** (Devpost: https://nebiusglobalaihackathon.devpost.com).
- **Autor:** desarrollador junior en Bogotá, Colombia. El proyecto también será la pieza principal de su portafolio de GitHub para entrevistas técnicas.
- **Categoría (track):** `Best Apps and Agents` *(cámbiala si se elige otra)*.
- **Idea del proyecto:** un asistente que convierte el problema de salud de un ciudadano colombiano con su EPS (medicamento negado, cita sin asignar, autorización demorada) en un **derecho de petición o una tutela** lista para radicar, con base legal buscada en la web y explicada en lenguaje simple. Arquitectura y funcionamiento actual: `README.md`.

### Fecha límite (no negociable)
- **Entrega final:** viernes **30 de octubre de 2026, 10:00 a.m. hora del Pacífico = 12:00 m. hora de Bogotá**.
- Después de esa hora no se puede modificar la entrega. Apunta a tener todo listo el **jueves 29 en la noche**.

---

## 2. Requisitos obligatorios del hackathon (si falla uno, el proyecto queda descalificado)

1. **Debe ser una aplicación de software funcional.**
2. **Debe correr en Nebius:** la app hace llamadas en tiempo de ejecución a la **API de inferencia de Nebius Token Factory**, o se despliega en Nebius AI Cloud (Serverless Jobs, Serverless Endpoints o DevPods).
3. **Debe usar al menos un modelo open source de NVIDIA** (familia **Nemotron**, idealmente Nemotron 3) a través de Nebius.
4. **Debe encajar de verdad en la categoría elegida.** No vale un proyecto genérico disfrazado.
5. **Repositorio público** en GitHub con **licencia open source visible** (usamos **MIT**, archivo `LICENSE` en la raíz).
6. **README en inglés** con instrucciones de instalación y ejecución, que explique **cómo se usa Nemotron** y **dónde aceleró el trabajo Token Factory**.
7. **Demo funcional en línea** (URL pública que los jurados puedan probar gratis hasta el 15 de diciembre de 2026).
8. **Video de menos de 3 minutos**, público en YouTube, mostrando la app funcionando, sin música con derechos de autor ni marcas de terceros.
9. **Todo el material de entrega en inglés** (o con traducción al inglés).
10. **Retroalimentación** sobre Nebius Token Factory, AI Cloud y los modelos de NVIDIA usados (hay un premio de US$100 para las mejores).

### Prohibido dentro de la app
- **No usar Claude, GPT, Gemini ni ningún modelo cerrado como el "cerebro" de la app.** La IA que razona dentro del producto debe ser Nemotron (u otro modelo abierto de NVIDIA) vía Nebius. Se pueden combinar con otros modelos abiertos disponibles en Token Factory (por ejemplo, embeddings), pero el núcleo debe ser NVIDIA.
- No usar código, datos ni imágenes sin licencia que lo permita.

---

## 3. Criterios de evaluación (todos pesan igual) — diseñar pensando en ellos

| Criterio | Qué significa para nosotros |
|---|---|
| **Implementación técnica** | Código limpio y bien usado Token Factory + Nemotron. Elegir el modelo adecuado para cada tarea. |
| **Diseño** | Producto completo y coherente, no una prueba de concepto. Interfaz clara, flujo de punta a punta. |
| **Impacto potencial** | Problema real, público concreto. La demo debe demostrar que lo resuelve. |
| **Calidad de la idea** | Uso creativo y no obvio de Nemotron. Mostrar que entendemos el problema. |

**Bonus opcional:** si se usa la **API de Tavily** con una llamada funcional en tiempo de ejecución, la app compite por un premio extra de US$3.000.

---

## 4. Stack técnico

- **Lenguaje:** Python 3.11+
- **Cliente del modelo:** librería `openai` de Python apuntando a Nebius Token Factory (su API es compatible con OpenAI).
- **Interfaz:** Streamlit (rápido de construir y fácil de desplegar).
- **Búsqueda web (opcional):** Tavily (`tavily-python`).
- **Despliegue de la demo:** Streamlit Community Cloud o Hugging Face Spaces. Nebius Serverless Endpoints es opcional.
- **Configuración:** `python-dotenv` para variables de entorno.
- **Validación de datos:** `pydantic` para validar las respuestas JSON del modelo.
- **Pruebas:** `pytest`.
- **Calidad:** `ruff` para formato y lint.

### Modelos — estrategia de enrutamiento
- **Nemotron 3 Nano:** tareas rápidas y frecuentes (clasificar, extraer campos, resumir textos cortos).
- **Nemotron 3 Super:** tareas intermedias y flujos de agentes.
- **Nemotron 3 Ultra:** solo cuando se necesita razonamiento difícil.
- Centraliza los nombres de modelo en `config.py`. **Nunca los escribas en varios archivos.**
- **No inventes nombres de modelos ni la URL base.** Cópialos exactamente del catálogo y la documentación de Nebius Token Factory. Si no los tienes, pregúntale al usuario.

---

## 5. Estructura del repositorio

```
.
├── app.py                 # Interfaz Streamlit (punto de entrada)
├── src/
│   ├── config.py          # Modelos, URL base, parámetros. Lee variables de entorno.
│   ├── llm.py             # Cliente único de Token Factory + funciones para llamar a Nemotron
│   ├── agent.py           # Lógica principal del agente / pipeline
│   ├── tools.py           # Herramientas del agente (p. ej. búsqueda Tavily)
│   └── prompts.py         # Todos los prompts en un solo lugar
├── tests/                 # Pruebas con pytest
├── data/samples/          # Datos de ejemplo SIN información personal real
├── docs/                  # Diagrama de arquitectura, capturas, GIF
├── .env.example           # Plantilla de variables (sin valores reales)
├── .gitignore
├── requirements.txt
├── LICENSE                # MIT
└── README.md              # En inglés
```

---

## 6. Reglas de seguridad (estrictas)

- **Nunca escribas API keys, tokens ni contraseñas en el código** ni en archivos que se suban a GitHub.
- Las claves van en `.env` (local) y en los "secrets" de la plataforma de despliegue.
- `.env` **siempre** en `.gitignore`. Mantén `.env.example` con los nombres de variables y valores vacíos:
  ```
  NEBIUS_API_KEY=
  NEBIUS_BASE_URL=
  TAVILY_API_KEY=
  ```
- Antes de cada commit, revisa que no se haya colado ninguna clave. Si alguna vez se sube una clave, **avisa al usuario de inmediato** para que la revoque.
- No uses datos personales reales en ejemplos (cédulas, NIT reales de personas, direcciones). Usa datos inventados.
- Valida y limita lo que el usuario sube a la app (tipo y tamaño de archivo).

---

## 7. Reglas de código

- Código, nombres de variables, comentarios y docstrings **en inglés** (el repo es para jurados y reclutadores internacionales).
- Funciones pequeñas, con type hints y docstrings cortos.
- Toda llamada al modelo pasa por `src/llm.py`. Ahí se manejan:
  - Errores de red y de la API, con mensajes claros para el usuario.
  - Reintentos con espera (máximo 3).
  - Timeouts.
  - Registro (logging) del modelo usado, tokens y latencia de cada llamada, para mostrar métricas. **Nunca** se registran claves ni el contenido completo de lo que sube el usuario.
- Cuando el modelo deba devolver datos estructurados, pídele JSON y **valídalo** (con `pydantic` o similar). Si falla, reintenta o muestra un error claro; nunca dejes que la app se caiga.
- No agregues dependencias innecesarias. Cada librería nueva va en `requirements.txt` con versión.
- Cuida los créditos: no hagas llamadas al modelo en bucles sin límite y usa Nano siempre que alcance.
- En las pruebas con `pytest`, **simula (mock) las llamadas a Nebius y Tavily**. Las pruebas no deben gastar créditos ni depender de la red.

---

## 8. Forma de trabajar con el usuario (importante)

El usuario está aprendiendo y **debe poder explicar cada parte del proyecto en una entrevista técnica**. Por eso:

- **Antes de escribir código grande, explica el plan en español** en pocas líneas y espera su visto bueno.
- **Después de cada cambio importante, explica en español qué hiciste y por qué**, con lenguaje sencillo. Menciona las alternativas que descartaste.
- Prefiere soluciones simples y entendibles sobre soluciones "inteligentes" difíciles de explicar.
- Si el usuario pide algo que rompe una regla del hackathon (por ejemplo, usar otro modelo como cerebro), adviértelo antes de hacerlo.
- Trabaja en pasos pequeños que se puedan probar. Después de cada paso, la app debe seguir funcionando.
- **Prioridad absoluta: llegar a la fecha límite con algo que funcione de punta a punta.** Las mejoras van después.

---

## 9. Git y commits

- Commits pequeños y frecuentes, con mensajes en inglés en formato convencional:
  `feat: add invoice field extraction`, `fix: handle empty PDF upload`, `docs: add architecture diagram`.
- Haz commit cada vez que algo nuevo funcione.
- La rama principal (`main`) siempre debe funcionar.
- El historial de commits debe mostrar trabajo real **dentro del periodo del hackathon** (26 ago – 30 oct 2026).

---

## 10. README (en inglés) — estructura obligatoria

1. **Título y una frase** que diga qué hace y para quién.
2. **Enlaces:** demo en vivo, video de YouTube, página de Devpost.
3. **The problem:** quién tiene el problema y por qué importa.
4. **The solution:** qué hace la app, con captura o GIF.
5. **How it uses NVIDIA Nemotron:** qué modelo se usa en cada paso y por qué (Nano vs Super vs Ultra).
6. **How it uses Nebius Token Factory** (y Serverless o Tavily, si aplica).
7. **Architecture:** diagrama simple del flujo.
8. **Metrics / evaluation:** latencia, tokens o costo por tarea y, si es posible, precisión en un pequeño set de prueba.
9. **Getting started:** requisitos, instalación, `.env`, cómo ejecutar, en pasos que funcionen en un entorno limpio.
10. **Limitations and next steps:** con honestidad.
11. **License:** MIT.

---

## 11. Plan de trabajo sugerido

| Día | Meta |
|---|---|
| **Dom 25 – Lun 26** | Inscripción en Devpost y Nebius Builder Program. Elegir la idea. Repo creado con estructura, `.env.example`, `LICENSE`. Primera llamada exitosa a Nemotron desde `llm.py`. |
| **Mar 27** | Lógica principal del agente funcionando desde la terminal, con datos de ejemplo. |
| **Mié 28** | Interfaz Streamlit de punta a punta. Manejo de errores. Pruebas básicas. |
| **Jue 29** | Despliegue de la demo pública. README completo. Diagrama. Grabar el video (menos de 3 min). |
| **Vie 30 (antes de 12:00 m. Bogotá)** | Revisión final con el checklist y envío del formulario en Devpost. |

---

## 12. Checklist final antes de entregar

- [ ] La app llama a Nemotron vía Nebius Token Factory en tiempo de ejecución.
- [ ] La demo pública funciona en una ventana de incógnito.
- [ ] El repo es público y la licencia MIT se ve en la sección "About" de GitHub.
- [ ] El README está en inglés y sus instrucciones funcionan desde cero.
- [ ] No hay ninguna clave en el repositorio (revisar también el historial de git).
- [ ] El video dura menos de 3 minutos, es público en YouTube y no tiene música con derechos.
- [ ] La descripción en Devpost está en inglés y menciona la categoría correcta.
- [ ] Se llenó la sección de retroalimentación sobre Nebius y NVIDIA.
- [ ] Se envió antes del viernes 30 de octubre a las 12:00 m. (hora de Bogotá).
