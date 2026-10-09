(function () {
  "use strict";
  var C = window.SITE.contact;
  var KEY = "racketgo_products";
  var P;
  try { P = JSON.parse(localStorage.getItem(KEY)); } catch (e) { P = null; }
  if (!Array.isArray(P)) P = window.PRODUCTS.slice();
  function save() { try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) { alert("Stockage plein : photos trop lourdes."); } }
  /* Migration des anciennes données (caracteristiques{} -> champs dédiés) */
  var SPECS = [["poids", "Poids"], ["forme", "Forme"], ["niveau", "Niveau"], ["equilibre", "Équilibre"], ["materiau", "Matériau"], ["annee", "Année"]];
  P = P.map(function (p) {
    if (p.caracteristiques) {
      SPECS.forEach(function (s) { if (p[s[0]] == null && p.caracteristiques[s[1]]) p[s[0]] = p.caracteristiques[s[1]]; });
      delete p.caracteristiques; delete p.statut;
    }
    if (p.etat === "Occasion") p.etat = "Très bon état";
    return p;
  });
  var admin = false;
  try { admin = sessionStorage.getItem("racketgo_admin") === "1"; } catch (e) {}
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
  var eur = function (n) { return n.toLocaleString("fr-FR") + " €"; };

  /* ---------- Icônes (logos simplifiés : remplaçables par les logos officiels) ---------- */
  var ICONS = {
    whatsapp: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M16 3a13 13 0 0 0-11 19.8L3 29l6.4-2A13 13 0 1 0 16 3zm0 2.4a10.6 10.6 0 1 1-5.6 19.6l-.4-.2-3.8 1.2 1.2-3.7-.3-.4A10.6 10.6 0 0 1 16 5.4zm-4 5.3c-.3 0-.7.1-1 .5-.4.4-1.300 1.300-1.300 3.100s1.300 3.600 1.500 3.800c.2.300 2.600 4.100 6.400 5.600 3.100 1.200 3.700 1 4.400.9.700-.1 2.200-.9 2.500-1.800.3-.9.3-1.600.2-1.800-.1-.2-.4-.3-.8-.5l-2.600-1.200c-.3-.1-.6-.2-.9.200-.3.400-1 1.200-1.200 1.500-.2.200-.4.300-.8.100-.4-.2-1.600-.6-3-1.900-1.100-1-1.900-2.200-2.100-2.600-.2-.4 0-.6.200-.8l.6-.7c.2-.2.200-.4.400-.6.100-.3.100-.5 0-.7l-1.100-2.700c-.3-.7-.6-.6-.9-.6z"/></svg>',
    facebook: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M18.500 29V17.500h3.900l.6-4.500h-4.500v-2.800c0-1.300.4-2.200 2.200-2.200H23V3.900c-.4 0-1.800-.2-3.400-.2-3.400 0-5.700 2.100-5.700 5.900V13H10v4.500h3.900V29z"/></svg>',
    leboncoin: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="currentColor"/><text x="16" y="21.500" text-anchor="middle" font-family="Arial" font-weight="800" font-size="13" fill="#ff6e14">lbc</text></svg>',
    vinted: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="currentColor"/><path d="M7 9h5l4 11 4-11h5l-7 16h-4z" fill="#09b1ba"/></svg>'
  };
  var LABELS = {
    whatsapp: ["Contacter sur WhatsApp", "WhatsApp"],
    facebook: ["Voir mon profil Facebook", "Facebook"],
    leboncoin: ["Voir mes annonces Leboncoin", "Leboncoin"],
    vinted: ["Voir ma boutique Vinted", "Vinted"]
  };

  function url(key, product) {
    var v = C[key];
    if (!v) return "";
    if (key === "whatsapp") {
      var msg = product
        ? "Bonjour, je suis intéressé(e) par la raquette « " + product.nom + " » à " + eur(product.prix) + "."
        : "Bonjour, je souhaite des informations sur vos raquettes de padel.";
      return "https://wa.me/" + v.replace(/\D/g, "") + "?text=" + encodeURIComponent(msg);
    }
    return v;
  }

  function buttons(product, short) {
    return Object.keys(LABELS).map(function (k) {
      var u = url(k, product);
      if (!u) return "";
      return '<a class="cbtn cbtn--' + k + '" href="' + esc(u) + '" target="_blank" rel="noopener">' +
        ICONS[k] + "<span>" + LABELS[k][short ? 1 : 0] + "</span></a>";
    }).join("");
  }

  /* ---------- Contacts globaux ---------- */
  document.querySelectorAll("[data-contact-buttons]").forEach(function (el) { el.innerHTML = buttons(null, false); });
  document.querySelectorAll("[data-contact-icons]").forEach(function (el) {
    el.innerHTML = Object.keys(LABELS).map(function (k) {
      var u = url(k); return u ? '<a href="' + esc(u) + '" target="_blank" rel="noopener" aria-label="' + LABELS[k][1] + '">' + ICONS[k] + "</a>" : "";
    }).join("");
  });
  var fab = $("[data-wa]");
  if (C.whatsapp) { fab.innerHTML = ICONS.whatsapp; fab.href = url("whatsapp"); fab.target = "_blank"; fab.rel = "noopener"; } else { fab.remove(); }
  $("#year").textContent = new Date().getFullYear();

  /* ---------- Catalogue ---------- */
  var grid = $("#grid"), empty = $("#empty");
  var fBrand = $("#f-brand"), fEtat = $("#f-etat"), fSort = $("#f-sort");
  function stockTxt(p) { return p.stock <= 0 ? "Rupture de stock (visible admin uniquement)" : "Stock : " + p.stock + (p.stock > 1 ? " raquettes" : " raquette"); }
  /* Règle : un visiteur ne voit que les raquettes en stock (stock > 0). */
  function visible(p) { return admin || p.stock > 0; }

  function refreshBrands() {
    var cur = fBrand.value;
    fBrand.innerHTML = '<option value="">Toutes</option>';
    P.map(function (p) { return p.marque; }).filter(function (m, i, a) { return a.indexOf(m) === i; }).sort()
      .forEach(function (m) { fBrand.insertAdjacentHTML("beforeend", "<option>" + esc(m) + "</option>"); });
    fBrand.value = cur;
  }
  function render() {
    refreshBrands();
    var list = P.filter(function (p) {
      return visible(p) && (!fBrand.value || p.marque === fBrand.value) && (!fEtat.value || p.etat === fEtat.value);
    });
    list.sort(function (a, b) { return (a.stock <= 0) - (b.stock <= 0); });
    if (fSort.value) list.sort(function (a, b) { return fSort.value === "asc" ? a.prix - b.prix : b.prix - a.prix; });
    empty.hidden = list.length > 0;
    grid.innerHTML = list.map(function (p) {
      var sold = p.stock <= 0;
      return '<article class="card' + (sold ? " card--sold" : "") + '">' +
        '<button class="card__media" data-id="' + esc(p.id) + '" aria-label="Voir la fiche de ' + esc(p.nom) + '">' +
        '<img src="' + esc(p.images[0]) + '" alt="' + esc(p.nom) + '" loading="lazy" width="400" height="400">' +
        '<span class="badge badge--' + (sold ? "sold" : "ok") + '">' + (sold ? "Rupture" : esc(p.etat)) + "</span></button>" +
        '<div class="card__body"><p class="card__brand">' + esc(p.marque) + " · " + esc(p.etat) + "</p>" +
        '<h3 class="card__title">' + esc(p.nom) + "</h3>" +
        '<p class="stock' + (sold ? " stock--out" : "") + '">' + stockTxt(p) + "</p>" +
        '<p class="card__price">' + eur(p.prix) + "</p>" +
        '<button class="btn ' + (sold ? "btn--ghost" : "btn--accent") + ' btn--block" data-id="' + esc(p.id) + '">' + (sold ? "Voir la fiche" : "Je suis intéressé") + "</button>" +
        (admin ? '<div class="card__admin"><button class="btn btn--ghost" data-edit="' + esc(p.id) + '">Modifier</button><button class="btn btn--danger" data-del="' + esc(p.id) + '">Supprimer</button></div>' : "") + "</div></article>";
    }).join("");
  }
  [fBrand, fEtat, fSort].forEach(function (f) { f.addEventListener("change", render); });
  render();

  /* ---------- Fiche détaillée ---------- */
  var modal = $("#modal"), body = $("#m-body");

  function open(id, fromHash) {
    var p = P.filter(function (x) { return x.id === id; })[0];
    if (!p || !visible(p)) return;
    var sold = p.stock <= 0;
    var specs = SPECS.filter(function (s) { return p[s[0]]; }).map(function (s) {
      return "<div><dt>" + s[1] + "</dt><dd>" + esc(p[s[0]]) + "</dd></div>";
    }).join("");
    body.innerHTML =
      '<div class="gallery"><img class="gallery__main" id="g-main" src="' + esc(p.images[0]) + '" alt="' + esc(p.nom) + '">' +
      '<div class="gallery__thumbs">' + p.images.map(function (src, i) {
        return '<button class="thumb' + (i === 0 ? " is-on" : "") + '" data-src="' + esc(src) + '" aria-label="Photo ' + (i + 1) + '"><img src="' + esc(src) + '" alt=""></button>';
      }).join("") + "</div></div>" +
      '<div class="detail"><span class="badge badge--' + (sold ? "sold" : "ok") + ' badge--static">' + (sold ? "Rupture" : esc(p.etat)) + "</span>" +
      '<p class="card__brand">' + esc(p.marque) + " · " + esc(p.etat) + "</p>" +
      '<h2 id="m-title">' + esc(p.nom) + "</h2>" +
      '<p class="detail__price">' + eur(p.prix) + "</p>" +
      '<p class="stock' + (sold ? " stock--out" : "") + '">' + stockTxt(p) + "</p>" +
      (p.description ? "<p>" + esc(p.description) + "</p>" : "") +
      "<h3>Caractéristiques</h3><dl class=\"specs\">" + specs + "</dl>" +
      '<div class="detail__contact"><p><strong>Cette raquette vous intéresse ?</strong> Écrivez-moi :</p>' +
      '<div class="contact-btns contact-btns--col">' + buttons(p, false) + "</div></div></div>";
    if (!modal.open) modal.showModal();
    modal.scrollTop = 0;
    if (!fromHash) history.replaceState(null, "", "#raquette=" + id);
  }
  function close() { if (modal.open) modal.close(); }
  modal.addEventListener("close", function () { if (location.hash.indexOf("#raquette=") === 0) history.replaceState(null, "", "#catalogue"); });
  $("#m-close").addEventListener("click", close);
  modal.addEventListener("click", function (e) { if (e.target === modal) close(); });
  grid.addEventListener("click", function (e) {
    var ed = e.target.closest("[data-edit]"), dl = e.target.closest("[data-del]");
    if (ed) return adminForm(ed.dataset.edit);
    if (dl) {
      var p = P.filter(function (x) { return x.id === dl.dataset.del; })[0];
      if (p && confirm("Supprimer « " + p.nom + " » ?")) { P = P.filter(function (x) { return x !== p; }); save(); render(); }
      return;
    }
    var b = e.target.closest("[data-id]"); if (b) open(b.dataset.id); });
  body.addEventListener("click", function (e) {
    var t = e.target.closest(".thumb"); if (!t) return;
    $("#g-main").src = t.dataset.src;
    body.querySelectorAll(".thumb").forEach(function (x) { x.classList.toggle("is-on", x === t); });
  });

  /* ---------- Administration (côté navigateur) ---------- */
  var am = $("#admin-modal"), ab = $("#admin-body"), bar = $("#admin-bar");
  am.querySelector("[data-close]").addEventListener("click", function () { am.close(); });
  function sha(txt) {
    if (!(window.crypto && crypto.subtle)) return Promise.reject(new Error("HTTPS requis"));
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(txt)).then(function (b) {
      return Array.prototype.map.call(new Uint8Array(b), function (x) { return ("0" + x.toString(16)).slice(-2); }).join("");
    });
  }
  function drawBar() {
    bar.hidden = !admin;
    if (!admin) return;
    bar.innerHTML = '<strong>Mode admin</strong><button class="btn btn--accent" id="a-add">+ Ajouter une raquette</button>' +
      '<button class="btn btn--ghost" id="a-export">Exporter (publier)</button>' +
      '<button class="btn btn--ghost" id="a-pw">Changer le mot de passe</button>' +
      '<button class="btn btn--ghost" id="a-reset">Réinitialiser</button>' +
      '<button class="btn btn--ghost" id="a-out">Déconnexion</button>';
  }
  bar.addEventListener("click", function (e) {
    var id = e.target.id;
    if (id === "a-add") adminForm();
    if (id === "a-out") { admin = false; try { sessionStorage.removeItem("racketgo_admin"); } catch (x) {} drawBar(); render(); }
    if (id === "a-reset" && confirm("Revenir au catalogue du fichier products.js ? Vos modifications locales seront perdues.")) {
      try { localStorage.removeItem(KEY); } catch (x) {} P = window.PRODUCTS.slice(); render();
    }
    if (id === "a-export") {
      var blob = new Blob(["window.PRODUCTS = " + JSON.stringify(P, null, 2) + ";\n"], { type: "text/javascript" });
      var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "products.js"; a.click();
      alert("Fichier products.js téléchargé. Remplacez js/products.js par ce fichier puis mettez le site en ligne pour que les visiteurs voient vos changements.");
    }
    if (id === "a-pw") {
      var n = prompt("Nouveau mot de passe :");
      if (n) sha(n).then(function (h) { prompt("Copiez cette empreinte dans js/config.js (adminHash) :", h); });
    }
  });
  $("#admin-open").addEventListener("click", function () {
    if (admin) { $("#catalogue").scrollIntoView(); return; }
    ab.innerHTML = '<form class="aform" id="login"><h2>Connexion admin</h2><label>Mot de passe<input type="password" id="pw" autocomplete="current-password" required></label>' +
      '<p class="aform__err" id="pw-err" hidden>Mot de passe incorrect.</p><button class="btn btn--accent btn--block">Se connecter</button></form>';
    am.showModal(); $("#pw").focus();
  });
  ab.addEventListener("submit", function (e) {
    e.preventDefault();
    if (e.target.id === "login") {
      sha($("#pw").value).then(function (h) {
        if (h === window.SITE.adminHash) {
          admin = true; try { sessionStorage.setItem("racketgo_admin", "1"); } catch (x) {}
          am.close(); drawBar(); render(); $("#catalogue").scrollIntoView();
        } else $("#pw-err").hidden = false;
      }, function () { $("#pw-err").textContent = "Connexion sécurisée (HTTPS) requise."; $("#pw-err").hidden = false; });
    } else if (e.target.id === "pform") saveForm(e.target);
  });

  function adminForm(id) {
    if (!admin) return;
    var p = P.filter(function (x) { return x.id === id; })[0] || { stock: 1, etat: "Très bon état", forme: "Diamant", niveau: "Confirmé", equilibre: "Moyen" };
    var opt = function (list, v) { return list.map(function (o) { return "<option" + (o === v ? " selected" : "") + ">" + o + "</option>"; }).join(""); };
    var txt = function (name, label, ph) { return '<label>' + label + '<input name="' + name + '" placeholder="' + (ph || "") + '" value="' + esc(p[name] || "") + '"></label>'; };
    ab.innerHTML = '<form class="aform" id="pform" data-id="' + esc(p.id || "") + '"><h2>' + (id ? "Modifier" : "Ajouter") + ' une raquette</h2>' +
      '<label>Nom<input name="nom" required value="' + esc(p.nom || "") + '"></label>' +
      '<label>Marque<input name="marque" required value="' + esc(p.marque || "") + '"></label>' +
      '<div class="aform__row"><label>Prix (€)<input name="prix" type="number" min="0" step="1" required value="' + (p.prix != null ? p.prix : "") + '"></label>' +
      '<label>Stock<input name="stock" type="number" min="0" step="1" required value="' + p.stock + '"></label></div>' +
      '<label>État<select name="etat">' + opt(["Neuf", "Très bon état"], p.etat) + '</select></label>' +
      '<fieldset class="aform__set"><legend>Caractéristiques techniques</legend>' +
      '<div class="aform__row">' + txt("poids", "Poids", "ex : 365 g") + '<label>Forme<select name="forme">' + opt(["Diamant", "Goutte d'eau", "Ronde"], p.forme) + '</select></label></div>' +
      '<div class="aform__row"><label>Niveau<select name="niveau">' + opt(["Débutant", "Intermédiaire", "Confirmé", "Expert"], p.niveau) + '</select></label>' +
      '<label>Équilibre<select name="equilibre">' + opt(["Bas", "Moyen", "Haut"], p.equilibre) + '</select></label></div>' +
      '<div class="aform__row">' + txt("materiau", "Matériau", "ex : Carbone 12K") + txt("annee", "Année", "ex : 2024") + '</div></fieldset>' +
      '<label>Remarque (facultatif)<input name="description" maxlength="200" value="' + esc(p.description || "") + '"></label>' +
      '<label>Photos' + (id ? " (laisser vide pour garder les actuelles)" : "") + '<input name="photos" type="file" accept="image/*" multiple></label>' +
      '<button class="btn btn--accent btn--block">Enregistrer</button></form>';

    if (!am.open) am.showModal();
  }
  function resize(file) {
    return new Promise(function (ok, ko) {
      var r = new FileReader();
      r.onerror = ko;
      r.onload = function () {
        var im = new Image(); im.onerror = ko;
        im.onload = function () {
          var k = Math.min(1, 800 / Math.max(im.width, im.height)), c = document.createElement("canvas");
          c.width = Math.round(im.width * k); c.height = Math.round(im.height * k);
          c.getContext("2d").drawImage(im, 0, 0, c.width, c.height);
          ok(c.toDataURL("image/jpeg", 0.75));
        };
        im.src = r.result;
      };
      r.readAsDataURL(file);
    });
  }
  function saveForm(f) {
    if (!admin) return;
    var d = new FormData(f), old = P.filter(function (x) { return x.id === f.dataset.id; })[0];
    var files = Array.prototype.slice.call(f.photos.files);
    Promise.all(files.map(resize)).then(function (imgs) {
      var item = {
        id: old ? old.id : String(d.get("nom")).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + Date.now().toString(36),
        nom: d.get("nom").trim(), marque: d.get("marque").trim(), prix: Number(d.get("prix")), stock: Math.max(0, parseInt(d.get("stock"), 10) || 0),
        etat: d.get("etat"), poids: d.get("poids").trim(), forme: d.get("forme"), niveau: d.get("niveau"), equilibre: d.get("equilibre"),
        materiau: d.get("materiau").trim(), annee: d.get("annee").trim(), description: d.get("description").trim(),
        images: imgs.length ? imgs : (old ? old.images : ["assets/img/raquette-1-a.svg"])
      };
      if (old) P[P.indexOf(old)] = item; else P.unshift(item);
      save(); am.close(); render();
    }, function () { alert("Image illisible."); });
  }
  drawBar();
  if (location.hash.indexOf("#raquette=") === 0) open(decodeURIComponent(location.hash.slice(10)), true);
})();
