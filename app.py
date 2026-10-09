"""Racket-Go: catalogue public et espace vendeur Streamlit."""

from __future__ import annotations

import base64
import hashlib
import html
import io
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError
from streamlit.errors import StreamlitSecretNotFoundError

import catalog
import security

ROOT = Path(__file__).resolve().parent
SHAPES = ["Ronde", "Goutte d’eau", "Diamant"]
CONTACTS = [("facebook_url", "Facebook", "f"), ("leboncoin_url", "Leboncoin", "L"), ("vinted_url", "Vinted", "V")]
PLACEHOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600"><rect width="600" height="600" rx="24" fill="#F1F4F2"/><g transform="rotate(-25 300 300)" fill="none" stroke="#9BAFA2" stroke-width="12"><ellipse cx="300" cy="235" rx="100" ry="130"/><path d="M270 360L278 450Q300 465 322 450L330 360"/><path d="M275 205h50M275 235h50M275 265h50" stroke-dasharray="1 22" stroke-linecap="round"/></g><text x="300" y="535" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#62756A">Photo à venir</text></svg>"""


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def euro(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " €"


def whatsapp_url(settings: dict, product: dict | None = None) -> str:
    number = settings.get("whatsapp_number", "")
    if not number:
        return ""
    message = "Bonjour, je souhaite des renseignements sur vos raquettes de padel."
    if product:
        message = f"Bonjour, je suis intéressé(e) par la raquette {product['name']} ({euro(product['price'])}). Est-elle toujours disponible ?"
    return f"https://wa.me/{number}?{urlencode({'text': message})}"


def image_path(relative: str) -> Path | None:
    """Résout uniquement les images du projet ou des uploads locaux."""
    if not relative:
        return None
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        return None
    if value.parts[0] == "assets":
        base = ROOT / "assets"
        path = ROOT / value
    elif value.parts[0] == "uploads":
        base = catalog.get_data_dir() / "uploads"
        path = catalog.get_data_dir() / value
    else:
        return None
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


@st.cache_data(show_spinner=False, max_entries=128)
def optimized_image(path: str, modified: int) -> str:
    """Réduit les images envoyées au navigateur sans toucher aux originaux."""
    del modified  # La date fait partie de la clé de cache.
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((800, 800))
        output = io.BytesIO()
        image.save(output, "JPEG", quality=84, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()


def image_uri(relative: str) -> str:
    path = image_path(relative)
    if path:
        try:
            return optimized_image(str(path), path.stat().st_mtime_ns)
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            pass
    return "data:image/svg+xml;base64," + base64.b64encode(PLACEHOLDER.encode()).decode()


def stock_badge(stock: int) -> str:
    if stock == 0:
        return '<span class="stock stock-empty">Épuisé</span>'
    if stock == 1:
        return '<span class="stock stock-last">Dernière pièce</span>'
    return f'<span class="stock stock-ready">Disponible · {stock}</span>'


def render_contacts(settings: dict, product: dict | None = None) -> None:
    wa = whatsapp_url(settings, product)
    others = [(label, symbol, settings.get(key, "")) for key, label, symbol in CONTACTS if settings.get(key)]
    if not wa and not others:
        return
    button = f'<a class="whatsapp-button" href="{escape(wa)}" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">↗</span> Me contacter sur WhatsApp</a>' if wa else ""
    links = "".join(f'<a class="contact-link contact-{label.lower()}" href="{escape(url)}" target="_blank" rel="noopener noreferrer"><span class="contact-icon" aria-hidden="true">{symbol}</span>{label}</a>' for label, symbol, url in others)
    if wa:
        links += f'<a class="contact-link contact-whatsapp" href="{escape(wa)}" target="_blank" rel="noopener noreferrer"><span class="contact-icon" aria-hidden="true">W</span>WhatsApp</a>'
    st.html(f'<section class="contacts" aria-label="Mes contacts">{button}<p class="contacts-label">Retrouvez-moi aussi sur</p><div class="contact-links">{links}</div></section>')


def render_header(settings: dict, compact: bool = False) -> None:
    st.html(f'<header class="brand-header"><a class="brand" href="?" aria-label="Accueil {escape(settings["site_name"])}"><span class="brand-mark" aria-hidden="true">↗</span><span>{escape(settings["site_name"])}</span></a><span class="brand-label">PADEL · SÉLECTION & STOCK</span></header>')
    if not compact:
        st.html(f'<section class="hero"><span class="eyebrow">LE PADEL, TOUT SIMPLEMENT</span><h1>{escape(settings["tagline"])}</h1><p>{escape(settings["description"])}</p><div class="hero-note"><span aria-hidden="true">●</span> Disponibilités affichées · Contact direct</div></section>')


def render_footer(settings: dict) -> None:
    st.html(f'<footer class="site-footer"><span>{escape(settings["site_name"])} · Passion padel.</span><a href="?admin=1">Espace vendeur</a></footer>')


def render_catalog(settings: dict) -> None:
    products = catalog.list_products()
    render_header(settings)
    if any(p["is_demo"] for p in products):
        st.html('<div class="demo-notice">Catalogue de démonstration : les raquettes, prix et stocks marqués « Démo » sont fictifs.</div>')
    st.html('<div id="catalogue" class="section-heading"><h2>Les raquettes</h2><span>Trouvez celle qui vous correspond.</span></div>')
    selected = st.pills("Style de jeu", ["Toutes", "Contrôle", "Polyvalentes", "Puissance"], default="Toutes", key="style_filter", label_visibility="collapsed")
    with st.expander("Rechercher et filtrer", expanded=False):
        search = st.text_input("Rechercher un modèle ou une marque", placeholder="Nom, marque…", key="search")
        col1, col2 = st.columns(2)
        brand = col1.selectbox("Marque", ["Toutes les marques"] + sorted({p["brand"] for p in products if p["brand"]}), key="brand_filter")
        condition = col2.selectbox("État", ["Tous les états", "Neuf", "Occasion"], key="condition_filter")
        available_only = st.toggle("Afficher uniquement les raquettes en stock", key="available_only")
    shape_filter = {"Contrôle": "Ronde", "Polyvalentes": "Goutte d’eau", "Puissance": "Diamant"}
    visible = [p for p in products if (not selected or selected == "Toutes" or p["shape"] == shape_filter[selected]) and (not search or search.casefold() in f'{p["name"]} {p["brand"]}'.casefold()) and (brand == "Toutes les marques" or p["brand"] == brand) and (condition == "Tous les états" or p["condition"] == condition) and (not available_only or p["stock"] > 0)]
    st.caption(f"{len(visible)} raquette{'s' if len(visible) != 1 else ''} affichée{'s' if len(visible) != 1 else ''}")
    if not visible:
        st.info("Aucune raquette ne correspond à votre recherche." if products else "Les prochaines raquettes arrivent bientôt. Revenez découvrir la sélection !")
    else:
        cards = []
        for product in visible:
            demo = '<span class="demo-tag">Démo</span>' if product["is_demo"] else ""
            weight = f' · {product["weight"]} g' if product["weight"] else ""
            cards.append(f'<article class="product-card"><a class="product-image-link" href="?product={product["id"]}" aria-label="Voir {escape(product["name"])}"><div class="product-image-wrap"><img src="{image_uri(product["image"])}" alt="{escape(product["name"])}" loading="lazy" width="800" height="800">{demo}</div></a><div class="product-info">{stock_badge(product["stock"])}<span class="product-brand">{escape(product["brand"])}</span><h3><a href="?product={product["id"]}">{escape(product["name"])}</a></h3><p class="product-specs">{escape(product["shape"])}{weight} · {escape(product["condition"])}</p><div class="product-bottom"><strong class="product-price">{euro(product["price"])}</strong><a class="product-open" href="?product={product["id"]}" aria-label="Détails de {escape(product["name"])}">Découvrir <span aria-hidden="true">↗</span></a></div></div></article>')
        st.html('<section class="product-grid" aria-label="Catalogue des raquettes">' + "".join(cards) + "</section>")
    render_contacts(settings)
    render_footer(settings)


def render_product(settings: dict, product_id: str) -> None:
    render_header(settings, compact=True)
    st.html('<a class="back-link" href="?">← Toutes les raquettes</a>')
    try:
        product = catalog.get_product(int(product_id))
    except (ValueError, TypeError):
        product = None
    if product is None:
        st.warning("Cette raquette n’est plus dans le catalogue.")
        render_footer(settings)
        return
    if product["is_demo"]:
        st.info("Raquette de démonstration : modèle, prix et stock fictifs.")
    photo, details = st.columns([1.05, 1], gap="large")
    with photo:
        st.html(f'<div class="detail-image"><img src="{image_uri(product["image"])}" alt="{escape(product["name"])}" width="800" height="800"></div>')
    with details:
        weight = f'{product["weight"]} g' if product["weight"] else "Non renseigné"
        st.html(f'<section class="product-detail"><span class="eyebrow">{escape(product["brand"])}</span><h1>{escape(product["name"])}</h1>{stock_badge(product["stock"])}<p class="detail-price">{euro(product["price"])}</p><dl class="spec-list"><div><dt>Forme</dt><dd>{escape(product["shape"])}</dd></div><div><dt>Poids</dt><dd>{weight}</dd></div><div><dt>État</dt><dd>{escape(product["condition"])}</dd></div></dl><p class="description">{escape(product["description"])}</p></section>')
        if product["stock"] == 0:
            st.caption("Ce modèle est actuellement épuisé. Contactez-moi pour connaître les prochaines disponibilités.")
        render_contacts(settings, product)
    render_footer(settings)


def read_secrets() -> dict:
    try:
        return st.secrets.to_dict()
    except (StreamlitSecretNotFoundError, FileNotFoundError):
        return {}


def credentials_signature(secrets: dict) -> str:
    hashed, plain = security.get_admin_credentials(secrets)
    return hashlib.sha256(f"{hashed or ''}:{plain or ''}".encode()).hexdigest()


def save_upload(upload) -> str:
    raw = upload.getvalue()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("La photo doit peser moins de 8 Mo.")
    try:
        with Image.open(io.BytesIO(raw)) as original:
            if original.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Utilisez une photo JPEG, PNG ou WebP.")
            if original.width * original.height > 25_000_000:
                raise ValueError("La photo est trop grande (25 mégapixels maximum).")
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((1600, 1600))
            filename = f"uploads/{uuid.uuid4().hex}.jpg"
            target = catalog.get_data_dir() / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, "JPEG", quality=90, optimize=True)
            return filename
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("La photo n’est pas une image JPEG, PNG ou WebP valide.") from error


def remove_unused_upload(relative: str) -> None:
    if not relative.startswith("uploads/") or any(p["image"] == relative for p in catalog.list_products()):
        return
    path = image_path(relative)
    if path:
        path.unlink(missing_ok=True)


def render_product_form(existing: dict | None) -> None:
    product = existing or {"name": "", "brand": "", "description": "", "price": 0.0, "stock": 1, "condition": "Neuf", "shape": SHAPES[0], "weight": 355, "image": "", "is_demo": False}
    st.subheader("Modifier la raquette" if existing else "Ajouter une raquette")
    with st.form("product_form", clear_on_submit=False):
        name = st.text_input("Nom du modèle", value=product["name"], max_chars=120)
        brand = st.text_input("Marque", value=product["brand"], max_chars=80)
        description = st.text_area("Description", value=product["description"], max_chars=2000, height=110)
        col1, col2 = st.columns(2)
        price = col1.number_input("Prix (€)", min_value=0.0, max_value=100000.0, value=float(product["price"]), step=1.0, format="%.2f")
        stock = col2.number_input("Quantité en stock", min_value=0, max_value=10000, value=int(product["stock"]), step=1)
        col1, col2 = st.columns(2)
        condition = col1.selectbox("État de la raquette", ["Neuf", "Occasion"], index=["Neuf", "Occasion"].index(product["condition"]))
        shape = col2.selectbox("Forme", SHAPES, index=SHAPES.index(product["shape"]))
        weight = st.number_input("Poids (g, 0 si inconnu)", min_value=0, max_value=1000, value=int(product["weight"]), step=1)
        upload = st.file_uploader("Photo de la raquette", type=["jpg", "jpeg", "png", "webp"], help="Photo facultative, 8 Mo maximum. Une nouvelle photo remplace l’ancienne.")
        if existing and product["image"]:
            st.caption("La photo actuelle est conservée si vous ne choisissez pas de nouveau fichier.")
        is_demo = st.checkbox("Produit de démonstration", value=bool(product["is_demo"]))
        submitted = st.form_submit_button("Enregistrer la raquette", type="primary", width="stretch")
    if submitted:
        new_image = ""
        try:
            if upload:
                new_image = save_upload(upload)
            values = {"name": name, "brand": brand, "description": description, "price": price, "stock": stock, "condition": condition, "shape": shape, "weight": weight, "image": new_image or product["image"], "is_demo": is_demo}
            if existing:
                values["id"] = existing["id"]
            saved_id = catalog.save_product(values)
        except ValueError as error:
            if new_image:
                remove_unused_upload(new_image)
            st.error(str(error))
        else:
            if new_image and existing:
                remove_unused_upload(existing["image"])
            if not existing:
                st.session_state["pending_product"] = saved_id
            st.session_state["flash"] = "Raquette enregistrée. Le catalogue et le stock sont à jour."
            st.rerun()
    if existing:
        st.divider()
        confirm = st.checkbox("Je confirme la suppression de cette raquette", key=f'delete_confirm_{existing["id"]}')
        if st.button("Supprimer la raquette", disabled=not confirm):
            catalog.delete_product(existing["id"])
            remove_unused_upload(existing["image"])
            st.session_state["flash"] = "Raquette supprimée du catalogue."
            st.rerun()


def render_settings_form(settings: dict) -> None:
    st.subheader("Votre vitrine et vos contacts")
    st.caption("Les liens laissés vides ne sont pas affichés sur le site public.")
    with st.form("settings_form"):
        site_name = st.text_input("Nom de la boutique", value=settings["site_name"], max_chars=80)
        tagline = st.text_input("Titre d’accueil", value=settings["tagline"], max_chars=160)
        description = st.text_area("Présentation courte", value=settings["description"], max_chars=600)
        whatsapp = st.text_input("Numéro WhatsApp international", value=settings["whatsapp_number"], placeholder="+33 6 12 34 56 78", help="Utilisez l’indicatif du pays : +33 6… pour la France, sans le 0 initial.")
        facebook = st.text_input("Lien Facebook", value=settings["facebook_url"], placeholder="https://www.facebook.com/…")
        leboncoin = st.text_input("Lien Leboncoin", value=settings["leboncoin_url"], placeholder="https://www.leboncoin.fr/…")
        vinted = st.text_input("Lien Vinted", value=settings["vinted_url"], placeholder="https://www.vinted.fr/…")
        submitted = st.form_submit_button("Enregistrer les contacts et la présentation", type="primary", width="stretch")
    if submitted:
        try:
            catalog.save_settings({"site_name": site_name, "tagline": tagline, "description": description, "whatsapp_number": whatsapp, "facebook_url": facebook, "leboncoin_url": leboncoin, "vinted_url": vinted})
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["flash"] = "Présentation et contacts enregistrés."
            st.rerun()


def render_admin(settings: dict) -> None:
    render_header(settings, compact=True)
    st.html('<a class="back-link" href="?">← Voir la vitrine</a>')
    st.title("Espace vendeur")
    secrets = read_secrets()
    if not security.credentials_configured(secrets):
        st.info("L’espace vendeur doit être activé avec un mot de passe privé avant de pouvoir modifier le catalogue.")
        st.caption("Suivez la section « Activer l’espace privé » du README du projet. Aucun mot de passe par défaut n’est fourni.")
        return
    signature = credentials_signature(secrets)
    logged_in = st.session_state.get("admin_signature") == signature and time.monotonic() - st.session_state.get("admin_login_at", 0) < 3600
    if not logged_in:
        st.session_state.pop("admin_signature", None)
        st.caption("Connectez-vous pour gérer vos raquettes, vos stocks et vos contacts.")
        attempts = st.session_state.get("login_attempts", [])
        allowed = security.login_allowed(attempts)
        with st.form("admin_login", clear_on_submit=True):
            password = st.text_input("Mot de passe vendeur", type="password")
            submitted = st.form_submit_button("Se connecter", type="primary", disabled=not allowed)
        if not allowed:
            st.warning("Trop de tentatives. Patientez cinq minutes avant de réessayer.")
            if st.button("Réessayer"):
                st.rerun()
        if message := st.session_state.pop("login_error", ""):
            st.error(message)
        if submitted and allowed:
            if security.authenticate(password, secrets):
                st.session_state["admin_signature"] = signature
                st.session_state["admin_login_at"] = time.monotonic()
                st.session_state["login_attempts"] = []
                st.rerun()
            else:
                st.session_state["login_attempts"] = attempts + [time.time()]
                st.session_state["login_error"] = "Mot de passe incorrect."
                st.rerun()
        return
    if st.button("Se déconnecter"):
        st.session_state.pop("admin_signature", None)
        st.session_state.pop("admin_login_at", None)
        st.rerun()
    if message := st.session_state.pop("flash", ""):
        st.success(message)
    products = catalog.list_products()
    cols = st.columns(3)
    cols[0].metric("Raquettes", len(products))
    cols[1].metric("Unités en stock", sum(p["stock"] for p in products))
    cols[2].metric("Modèles disponibles", sum(p["stock"] > 0 for p in products))
    tab_products, tab_settings = st.tabs(["Raquettes et stock", "Présentation et contacts"])
    with tab_products:
        choices = {0: "＋ Ajouter une raquette", **{p["id"]: f'{p["name"]} — {p["stock"]} en stock' for p in products}}
        if pending := st.session_state.pop("pending_product", None):
            st.session_state["managed_product"] = pending
        selected = st.selectbox("Raquette à gérer", list(choices), format_func=choices.get, key="managed_product")
        render_product_form(catalog.get_product(selected) if selected else None)
    with tab_settings:
        render_settings_form(settings)


def main() -> None:
    catalog.init_db()
    settings = catalog.get_settings()
    st.set_page_config(page_title=f'{settings["site_name"]} · Raquettes de padel', page_icon="🎾", layout="centered", initial_sidebar_state="collapsed")
    st.html(f'<style>{(ROOT / "styles.css").read_text()}</style>')
    if st.query_params.get("admin") == "1":
        render_admin(settings)
    elif product_id := st.query_params.get("product"):
        render_product(settings, product_id)
    else:
        render_catalog(settings)


if __name__ == "__main__":
    main()
