/* Tests Node du composant arbitres (logique pure). Lancer : node static/arbitres.test.js */
const A = require("./arbitres.js");
let ko = 0;
function check(name, cond) { console.log((cond ? "  PASS " : "  FAIL ") + name); if (!cond) ko++; }

check("5 niveaux officiels", A.NIVEAUX.map(n => n.value).join(",") ===
  "regional_formation,regional,national_formation,national,international");

// 0 requis -> valide même sans saisie
check("0 requis = ok", A.valider([], 0).ok === true);

// 1 requis, complet -> ok
check("1 requis complet = ok",
  A.valider([{ nom: "Petit", prenom: "Marc", club: "Nancy", niveau: "national" }], 1).ok === true);

// 1 requis, manquant -> ko
check("1 requis vide = ko", A.valider([], 1).ok === false);

// champ incomplet -> ko
check("champ manquant = ko",
  A.valider([{ nom: "Petit", prenom: "", club: "Nancy", niveau: "national" }], 1).ok === false);

// niveau invalide (ancien D/C/B/A) -> ko
check("niveau 'B' rejeté",
  A.valider([{ nom: "X", prenom: "Y", club: "Z", niveau: "B" }], 1).ok === false);

console.log(ko === 0 ? "=> arbitres.js : tous les cas OK" : "=> " + ko + " ÉCHEC(S)");
process.exit(ko === 0 ? 0 : 1);
