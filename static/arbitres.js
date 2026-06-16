/*
 * arbitres.js — Composant réutilisable de saisie des arbitres (2.2b).
 *
 * Génère `nombre` blocs Nom/Prénom/Club/Niveau, avec les 5 niveaux officiels
 * LREGE. Utilisé par les formulaires M15/Vétérans/Individuels/Équipes (2.3-2.6).
 *
 * API :
 *   Arbitres.NIVEAUX                       -> [{value,label}]
 *   Arbitres.render(container, nombre, existing=[])
 *   Arbitres.collect(container)            -> [{nom,prenom,club,niveau}]
 *   Arbitres.valider(liste, nombre)        -> {ok, errors:[...]}
 */
(function (root) {
  "use strict";

  var NIVEAUX = [
    { value: "regional_formation", label: "Régional en formation" },
    { value: "regional", label: "Régional" },
    { value: "national_formation", label: "National en formation" },
    { value: "national", label: "National" },
    { value: "international", label: "International" },
  ];

  function escapeAttr(s) {
    return String(s == null ? "" : s).replace(/"/g, "&quot;");
  }

  function niveauOptions(selected) {
    var opts = '<option value="">Niveau…</option>';
    NIVEAUX.forEach(function (n) {
      var sel = n.value === selected ? " selected" : "";
      opts += '<option value="' + n.value + '"' + sel + ">" + n.label + "</option>";
    });
    return opts;
  }

  function render(container, nombre, existing) {
    existing = existing || [];
    container.innerHTML = "";
    if (!nombre || nombre <= 0) {
      container.innerHTML = '<p class="arb-vide">Pas d\'arbitre requis pour cette épreuve.</p>';
      return;
    }
    for (var i = 0; i < nombre; i++) {
      var a = existing[i] || {};
      var fs = document.createElement("fieldset");
      fs.className = "arbitre-box";
      fs.dataset.idx = i;
      fs.innerHTML =
        "<legend>Arbitre " + (i + 1) + "</legend>" +
        '<input class="arb-nom" placeholder="Nom" value="' + escapeAttr(a.nom) + '">' +
        '<input class="arb-prenom" placeholder="Prénom" value="' + escapeAttr(a.prenom) + '">' +
        '<input class="arb-club" placeholder="Club" value="' + escapeAttr(a.club) + '">' +
        '<select class="arb-niveau">' + niveauOptions(a.niveau) + "</select>";
      container.appendChild(fs);
    }
  }

  function collect(container) {
    var boxes = container.querySelectorAll("fieldset.arbitre-box");
    return Array.prototype.map.call(boxes, function (fs) {
      return {
        nom: fs.querySelector(".arb-nom").value.trim(),
        prenom: fs.querySelector(".arb-prenom").value.trim(),
        club: fs.querySelector(".arb-club").value.trim(),
        niveau: fs.querySelector(".arb-niveau").value,
      };
    });
  }

  function valider(liste, nombre) {
    liste = liste || [];
    var errors = [];
    var valides = NIVEAUX.map(function (n) { return n.value; });
    if (liste.length < nombre) {
      errors.push(nombre + " arbitre(s) requis (saisis : " + liste.length + ").");
    }
    liste.forEach(function (a, i) {
      if (!a.nom || !a.prenom || !a.club || !a.niveau) {
        errors.push("Arbitre " + (i + 1) + " : champs incomplets.");
      } else if (valides.indexOf(a.niveau) === -1) {
        errors.push("Arbitre " + (i + 1) + " : niveau invalide.");
      }
    });
    return { ok: errors.length === 0, errors: errors };
  }

  var api = { NIVEAUX: NIVEAUX, render: render, collect: collect, valider: valider };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.Arbitres = api;
})(typeof window !== "undefined" ? window : null);
