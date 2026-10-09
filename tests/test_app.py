"""Exercise the public catalogue and private seller workflow in Streamlit."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import catalog


APP = Path(__file__).resolve().parents[1] / "app.py"
FIXTURE_PASSWORD = "fixture-only-padel-123"


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Never read or alter the seller's actual catalogue or credentials."""
    monkeypatch.setenv("RACKET_GO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("RACKET_GO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("RACKET_GO_ADMIN_PASSWORD_HASH", raising=False)


def app(**query_params):
    tested = AppTest.from_file(str(APP), default_timeout=10)
    tested.query_params.update(query_params)
    tested.run()
    assert not tested.exception
    return tested


def labelled(elements, label):
    return next(element for element in elements if element.label == label)


def html_output(tested):
    return "\n".join(element.proto.body for element in tested.get("html"))


def login(monkeypatch):
    monkeypatch.setenv("RACKET_GO_ADMIN_PASSWORD", FIXTURE_PASSWORD)
    tested = app(admin="1")
    labelled(tested.text_input, "Mot de passe vendeur").set_value(FIXTURE_PASSWORD)
    labelled(tested.button, "Se connecter").click().run()
    assert not tested.exception
    assert labelled(tested.button, "Se déconnecter")
    return tested


def test_initial_catalogue_and_available_stock_filter():
    tested = app()
    output = html_output(tested)
    assert tested.caption[0].value == "4 raquettes affichées"
    assert output.count('<article class="product-card">') == 4
    assert "Catalogue de démonstration" in output
    assert "Dernière pièce" in output
    assert "Épuisé" in output
    assert 'class="contacts"' not in output

    tested.toggle(key="available_only").set_value(True).run()
    assert not tested.exception
    assert tested.caption[0].value == "3 raquettes affichées"
    assert html_output(tested).count('<article class="product-card">') == 3
    assert "Épuisé" not in html_output(tested)


def test_search_and_play_style_filters_are_combined():
    tested = app()
    tested.get("button_group")[0].set_value("Puissance").run()
    assert tested.caption[0].value == "2 raquettes affichées"

    tested.text_input(key="search").set_value("pRo").run()
    assert not tested.exception
    assert tested.caption[0].value == "1 raquette affichée"
    assert '<h3><a href="?product=4">Pro</a></h3>' in html_output(tested)

    tested.get("button_group")[0].set_value("Contrôle").run()
    assert tested.caption[0].value == "0 raquettes affichées"
    assert tested.info[0].value == "Aucune raquette ne correspond à votre recherche."
    assert 'class="product-card"' not in html_output(tested)


def test_product_detail_displays_price_specs_and_empty_stock():
    tested = app(product="4")
    assert "Raquette de démonstration" in tested.info[0].value
    output = html_output(tested)
    assert "<h1>Pro</h1>" in output
    assert "229,00 €" in output
    assert "Diamant" in output
    assert "365 g" in output
    assert "Épuisé" in output
    assert "actuellement épuisé" in tested.caption[0].value


@pytest.mark.parametrize("product_id", ["unknown", "999999", "0", "-1", str(2**64)])
def test_invalid_or_missing_product_is_handled(product_id):
    tested = app(product=product_id)
    assert tested.warning[0].value == "Cette raquette n’est plus dans le catalogue."
    assert 'class="product-detail"' not in html_output(tested)


def test_admin_without_credentials_exposes_no_mutation_forms():
    before = catalog.list_products()
    tested = app(admin="1")
    assert "activé avec un mot de passe privé" in tested.info[0].value
    assert not tested.text_input
    assert not tested.button
    assert not tested.number_input
    assert catalog.list_products() == before


def test_wrong_password_cannot_open_seller_forms(monkeypatch):
    monkeypatch.setenv("RACKET_GO_ADMIN_PASSWORD", FIXTURE_PASSWORD)
    tested = app(admin="1")
    labelled(tested.text_input, "Mot de passe vendeur").set_value("wrong-fixture-password")
    labelled(tested.button, "Se connecter").click().run()
    assert not tested.exception
    assert tested.error[0].value == "Mot de passe incorrect."
    assert [element.label for element in tested.text_input] == ["Mot de passe vendeur"]
    assert not tested.number_input
    assert "admin_signature" not in tested.session_state


def test_seller_can_add_edit_and_publish_stock(monkeypatch):
    tested = login(monkeypatch)
    labelled(tested.text_input, "Nom du modèle").set_value("Raquette de test réelle")
    labelled(tested.text_input, "Marque").set_value("Marque test")
    labelled(tested.text_area, "Description").set_value("Raquette vérifiée pour le test du catalogue.")
    labelled(tested.number_input, "Prix (€)").set_value(145.5)
    labelled(tested.number_input, "Quantité en stock").set_value(2)
    labelled(tested.selectbox, "État de la raquette").set_value("Occasion")
    labelled(tested.selectbox, "Forme").set_value("Goutte d’eau")
    labelled(tested.number_input, "Poids (g, 0 si inconnu)").set_value(360)
    labelled(tested.button, "Enregistrer la raquette").click().run()
    assert not tested.exception
    assert "Raquette enregistrée" in tested.success[0].value

    product = next(product for product in catalog.list_products() if not product["is_demo"])
    assert labelled(tested.selectbox, "Raquette à gérer").value == product["id"]
    assert product["name"] == "Raquette de test réelle"
    assert product["stock"] == 2
    assert product["price"] == 145.5
    assert product["condition"] == "Occasion"
    assert product["shape"] == "Goutte d’eau"
    assert product["weight"] == 360
    public = app(product=str(product["id"]))
    assert "Disponible · 2" in html_output(public)
    assert "145,50 €" in html_output(public)
    assert not public.info

    labelled(tested.selectbox, "Raquette à gérer").set_value(product["id"]).run()
    assert labelled(tested.text_input, "Nom du modèle").value == product["name"]
    labelled(tested.number_input, "Quantité en stock").set_value(0)
    labelled(tested.button, "Enregistrer la raquette").click().run()
    assert not tested.exception
    assert catalog.get_product(product["id"])["stock"] == 0
    public.run()
    assert "Épuisé" in html_output(public)
    assert "actuellement épuisé" in public.caption[0].value

    catalogue = app()
    catalogue.toggle(key="available_only").set_value(True).run()
    assert "Raquette de test réelle" not in html_output(catalogue)
    assert catalogue.caption[0].value == "3 raquettes affichées"


def test_settings_links_publish_only_after_valid_submission(monkeypatch):
    tested = login(monkeypatch)
    labelled(tested.text_input, "Nom de la boutique").set_value("Padel test")
    labelled(tested.text_input, "Numéro WhatsApp international").set_value("+33 6 12 34 56 78")
    labelled(tested.text_input, "Lien Facebook").set_value("https://www.facebook.com/padel-test")
    labelled(tested.text_input, "Lien Leboncoin").set_value("https://www.leboncoin.fr/profile/padel-test")
    labelled(tested.text_input, "Lien Vinted").set_value("https://www.vinted.fr/member/padel-test")
    labelled(tested.button, "Enregistrer les contacts et la présentation").click().run()
    assert not tested.exception
    assert tested.success[0].value == "Présentation et contacts enregistrés."
    settings = catalog.get_settings()
    assert settings["site_name"] == "Padel test"
    assert settings["whatsapp_number"] == "33612345678"
    public = app()
    output = html_output(public)
    assert "Padel test" in output
    assert "https://wa.me/33612345678?text=" in output
    for name in ("facebook_url", "leboncoin_url", "vinted_url"):
        assert f'href="{settings[name]}"' in output

    labelled(tested.text_input, "Nom de la boutique").set_value("Must not save")
    labelled(tested.text_input, "Lien Facebook").set_value("javascript:alert(1)")
    labelled(tested.button, "Enregistrer les contacts et la présentation").click().run()
    assert not tested.exception
    assert tested.error
    assert catalog.get_settings() == settings
    public.run()
    assert "javascript:" not in html_output(public)
    assert "Must not save" not in html_output(public)


def test_logout_closes_seller_forms(monkeypatch):
    tested = login(monkeypatch)
    labelled(tested.button, "Se déconnecter").click().run()
    assert not tested.exception
    assert [element.label for element in tested.text_input] == ["Mot de passe vendeur"]
    assert not tested.number_input
    assert "admin_signature" not in tested.session_state
