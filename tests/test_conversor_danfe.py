import unittest

from conversor_danfe import parse_invoice, safe_filename


AUTHORIZED_NFE = b'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35123456789012345678901234567890123456789012" versao="4.00">
      <ide>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>1234</nNF>
        <dhEmi>2026-09-08T09:00:00-03:00</dhEmi>
      </ide>
      <dest><xNome>EMPRESA TESTE LTDA</xNome></dest>
    </infNFe>
  </NFe>
  <protNFe>
    <infProt>
      <chNFe>35123456789012345678901234567890123456789012</chNFe>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>'''


class InvoiceParsingTests(unittest.TestCase):
    def test_parse_authorized_invoice(self):
        info = parse_invoice(AUTHORIZED_NFE)
        self.assertEqual(info.number, "1234")
        self.assertEqual(info.series, "1")
        self.assertEqual(info.recipient, "EMPRESA TESTE LTDA")
        self.assertEqual(info.model, "55")
        self.assertTrue(info.authorized)

    def test_rejects_nfe_model_65(self):
        xml = AUTHORIZED_NFE.replace(b"<mod>55</mod>", b"<mod>65</mod>")
        with self.assertRaisesRegex(ValueError, "Modelo 65"):
            parse_invoice(xml)

    def test_rejects_non_nfe_xml(self):
        with self.assertRaisesRegex(ValueError, "não é uma NF-e"):
            parse_invoice(b"<pedido><numero>1</numero></pedido>")


class FilenameTests(unittest.TestCase):
    def test_removes_invalid_windows_characters(self):
        self.assertEqual(safe_filename('NF: 10 / Cliente?'), "NF 10 Cliente")

    def test_uses_fallback_for_empty_name(self):
        self.assertEqual(safe_filename('   '), "SEM NOME")


if __name__ == "__main__":
    unittest.main()
