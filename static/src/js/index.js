  (function () {
    // Evitar doble init si Odoo reinyecta assets
    if (window.__pmantChecklistInit) return;
    window.__pmantChecklistInit = true;

    document.addEventListener("DOMContentLoaded", function () {
      const form = document.getElementById("checklist-form");
      if (!form) return;

      // 1) Comentario por pregunta (delegación de eventos)
      form.addEventListener("change", function (ev) {
        const chk = ev.target.closest(".toggle-comentario");
        if (chk && form.contains(chk)) {
          const id = chk.getAttribute("data-id");
          const box = document.getElementById("cmt_box_" + id);
          if (box) box.style.display = chk.checked ? "block" : "none";
        }
      });

      // 2) (Opcional) Comentario final si existe en el DOM
      const toggleFinal = document.getElementById("toggleComentarioFinal");
      const boxFinal = document.getElementById("comentarioFinalBox");
      if (toggleFinal && boxFinal) {
        toggleFinal.addEventListener("change", function () {
          boxFinal.style.display = toggleFinal.checked ? "block" : "none";
        });
      }

      // 3) Validación ligera de radios Sí/No (además del required nativo)
      form.addEventListener(
        "submit",
        function (e) {
          const radios = form.querySelectorAll('input[type="radio"]');
          const groupNames = new Set(Array.from(radios).map((r) => r.name));
          const missing = [];
          groupNames.forEach((name) => {
            // Evita validar grupos que no sean de sí/no si los tienes
            if (!name.includes("_si_no")) return;
            if (!form.querySelector('input[name="' + name + '"]:checked')) {
              missing.push(name);
            }
          });
          if (missing.length) {
            e.preventDefault();
            alert("Por favor, responde todas las preguntas de tipo Sí/No.");
          }
        },
        { passive: false }
      );
    });
  })();
