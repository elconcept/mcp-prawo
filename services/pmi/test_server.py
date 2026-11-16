"""Local unit checks; live HTML smoke tests are run through MCP against PrawMi."""
import unittest

from bs4 import BeautifulSoup

from server import article_id, ruling_slug, safe_slug, fold, extract_article_content, article_source_metadata


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
        self.assertEqual(extract_article_content(root), "§ 1. A\\n§ 2. B")

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


if __name__ == "__main__":
    unittest.main()
