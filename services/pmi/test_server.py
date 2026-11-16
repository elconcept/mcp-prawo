"""Local unit checks; live HTML smoke tests are run through MCP against PrawMi."""
import unittest

from bs4 import BeautifulSoup

from server import (article_id, ruling_slug, safe_slug, fold, extract_article_content,
                    article_source_metadata, act_source_metadata, page_metadata,
                    article_judgments, article_change_history, article_editorial_material,
                    adjacent_article_links, ACT_NODE_ID)


class PmiParsersTest(unittest.TestCase):
    def test_article_identifiers(self):
        for raw in ("23", "art-23", "art. 23"):
            self.assertEqual(article_id(raw), "art-23")
        self.assertEqual(article_id("4a"), "art-4a")
        self.assertEqual(article_id("art-4a"), "art-4a")

    def test_safe_slugs(self):
        self.assertEqual(safe_slug("kodeks-postepowania-karnego"), "kodeks-postepowania-karnego")
        for bad in ("/../../etc/passwd", "https://evil.com", "../ustawa"):
            with self.assertRaises(ValueError):
                safe_slug(bad)

    def test_ruling_signature(self):
        self.assertEqual(ruling_slug("XII Ko 26/23"), "xii-ko-26-23")
        self.assertEqual(ruling_slug("III OSK 533/24"), "iii-osk-533-24")
        self.assertEqual(ruling_slug("Sygn. akt XII Ko 26/23"), "xii-ko-26-23")

    def test_polish_normalization(self):
        self.assertEqual(fold("Postępowanie karne"), "postepowanie karne")


    def test_article_multi_paragraph_layout(self):
        html = '<article id="przepis"><div class="mt-6 space-y-5"><p>§ 1. A</p><p>§ 2. B</p></div></article>'
        root = BeautifulSoup(html, "html.parser").select_one("article#przepis")
        self.assertEqual(extract_article_content(root), "§ 1. A\n§ 2. B")

    def test_article_single_paragraph_layout(self):
        html = '<article id="przepis"><div class="mt-6 rounded-2xl"><p class="text-xl leading-relaxed">Kto z winy swej wyrządził szkodę.</p></div></article>'
        root = BeautifulSoup(html, "html.parser").select_one("article#przepis")
        self.assertEqual(extract_article_content(root), "Kto z winy swej wyrządził szkodę.")

    def test_article_repealed(self):
        html = '<article id="przepis"><div class="mt-6 rounded-2xl"><p class="text-xl leading-relaxed">(uchylony)</p></div></article>'
        root = BeautifulSoup(html, "html.parser").select_one("article#przepis")
        self.assertEqual(extract_article_content(root), "(uchylony)")

    def test_article_metadata_is_original_publication(self):
        html = """<script type="application/ld+json">
        {"@type": "Article", "dateModified": "2026-07-12",
        "isPartOf": {"legislationIdentifier": "Dz.U. 1964 poz. 93"}}
        </script>"""
        result = article_source_metadata(BeautifulSoup(html, "html.parser"))
        self.assertEqual(result["publication"], "Dz.U. 1964 poz. 93")
        self.assertEqual(result["original_eli_derived"], "DU/1964/93")
        self.assertEqual(result["source_modified_at"], "2026-07-12")
        self.assertEqual(result["publication_scope"], "original_act_not_current_consolidation")

    def test_article_missing_text_does_not_return_ui(self):
        html = '<article id="przepis"><p>Kopiuj link, zapytaj AI</p></article>'
        root = BeautifulSoup(html, "html.parser").select_one("article#przepis")
        with self.assertRaises(RuntimeError):
            extract_article_content(root)


    def test_combined_article_range_is_in_act(self):
        self.assertTrue(ACT_NODE_ID.fullmatch("art-28-30"))
        self.assertTrue(ACT_NODE_ID.fullmatch("art-6a"))
        self.assertFalse(ACT_NODE_ID.fullmatch("art-invalid"))

    def test_legislation_jsonld_and_canonical(self):
        html = """<html lang="pl"><head>
        <meta name="description" content="Opis ustawy"/>
        <meta property="og:title" content="Akt prawny"/>
        <link rel="canonical" href="https://prawmi.pl/ustawa/test"/>
        <script type="application/ld+json">
        {"@type":"Legislation","legislationType":"Ustawa",
        "legislationIdentifier":"Dz.U. 2022 poz. 1095",
        "jurisdiction":{"name":"Polska"}}
        </script></head><body><main>
        <a href="https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20220001095">ISAP</a>
        </main></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        meta = page_metadata(soup)
        law = act_source_metadata(soup)
        self.assertEqual(meta["html_meta"]["description"], "Opis ustawy")
        self.assertEqual(meta["html_meta"]["og:title"], "Akt prawny")
        self.assertEqual(meta["canonical_url"], "https://prawmi.pl/ustawa/test")
        self.assertEqual(meta["official_links"][0]["label"], "ISAP")
        self.assertEqual(law["original_eli_derived"], "DU/2022/1095")
        self.assertEqual(law["jurisdiction"], "Polska")
        self.assertEqual(law["publication_scope"], "original_act_not_current_consolidation")

    def test_judgment_cards_return_evidence_and_deduplicate_links(self):
        html = """<html><head><title>Art. 245. 10 orzeczeń</title></head>
        <body><main><section id="orzeczenia">
        <button>Wszystkie tematy</button><button>prawa zatrzymanego</button>
        <article><div class="flex flex-wrap">
        <span>II AKa 230/22</span><span aria-hidden="true">·</span>
        <span>Sąd Apelacyjny</span><time datetime="2022-09-22">22 września 2022</time></div>
        <h3><a href="/orzeczenie/ii-aka-230-22">Ochrona zatrzymanego</a></h3>
        <blockquote>art. 245 k.p.k. i kontakt z obrońcą</blockquote>
        <a href="/orzeczenie/ii-aka-230-22">Czytaj orzeczenie</a></article>
        </section></main></body></html>"""
        data = article_judgments(BeautifulSoup(html, "html.parser"))
        self.assertEqual(data["linked_judgments_count"], 1)
        self.assertEqual(data["site_claimed_judgments_count"], 10)
        self.assertEqual(data["judgment_topic_filters"], ["prawa zatrzymanego"])
        case = data["related_judgments"][0]
        self.assertEqual(case["signature"], "II AKa 230/22")
        self.assertEqual(case["court"], "Sąd Apelacyjny")
        self.assertEqual(case["date"], "2022-09-22")
        self.assertEqual(case["document_id"], "pmi:ruling:ii-aka-230-22")
        self.assertIn("kontakt z obrońcą", case["excerpt"])

    def test_missing_judgment_section_is_not_inferred(self):
        soup = BeautifulSoup('<main><a href="/orzeczenie/example">Przykład</a></main>', "html.parser")
        self.assertEqual(article_judgments(soup), {})

    def test_article_change_history_distinguishes_detection_from_enactment(self):
        html = """<section id="historia-zmian">
        <p>Daty to dni, w których PrawMi wykryło zmianę. Nie są datami wejścia w życie.</p>
        <ol><li><div><section><div><h3>Zmiana wykryta 12.09.2026</h3>
        <span>dodany</span></div><p>Nowy artykuł.</p></section></div></li></ol>
        </section>"""
        data = article_change_history(BeautifulSoup(html, "html.parser"))
        self.assertIn("Nie są datami", data["history_detection_note"])
        self.assertEqual(data["article_change_history"][0]["detected_on"], "12.09.2026")
        self.assertEqual(data["article_change_history"][0]["change_type"], "dodany")

    def test_editorial_separate_from_law_and_faq(self):
        html = """<div><section id="wyjasnienie"><h2>Wyjaśnienie przepisu</h2>
        <div><p>Niezweryfikowany komentarz redakcyjny.</p></div></section>
        <section id="pytania"><details><summary><span>Co to znaczy?</span></summary>
        <p>Tekst pytania i odpowiedzi.</p></details></section></div>"""
        data = article_editorial_material(BeautifulSoup(html, "html.parser"))
        self.assertEqual(data["site_explanation"]["authority"],
                         "unverified_site_editorial_not_primary_law")
        self.assertEqual(data["site_faq"]["entries"][0]["question"], "Co to znaczy?")
        self.assertIn("Niezweryfikowany", data["site_explanation"]["text"])

    def test_adjacent_articles_are_actual_links_only(self):
        soup = BeautifulSoup("""<main>
        <a href="/ustawa/kodeks-cywilny/art-414">Poprzedni</a>
        <a href="/ustawa/kodeks-cywilny/art-416">Następny</a>
        <a href="/ustawa/kodeks-karny/art-1">Nie ten akt</a>
        </main>""", "html.parser")
        links = adjacent_article_links(soup, "kodeks-cywilny")
        self.assertEqual([x["article"] for x in links], ["414", "416"])



if __name__ == "__main__":
    unittest.main()
