import easyocr
import numpy as np
import re
from PIL import Image
from modules.data.receipt_data import ItemData, ReceiptData
from .base import AIModel

class EasyOCRModel(AIModel):
    """Receipt reader based on EasyOCR."""

    def __init__(self) -> None:
        """Initialize the model."""
        self.reader = easyocr.Reader(['id', 'en'], gpu=False)

    def run(self, image: Image.Image) -> ReceiptData:
        """Retrieve data from the receipt.

        Args:
            image (Image.Image): the receipt photo image

        Returns:
            ReceiptData: parsed receipt data
        """
        image_np = np.array(image)
        raw_text_list = self.reader.readtext(image_np, detail=0)

        # Parsing
        return self._parse_raw_text(raw_text_list)

    def _parse_raw_text(self, text_list: list[str]) -> ReceiptData:
        """Simple parsing logic to convert text list to ReceiptData."""
        items = []
        total_accumulated = 0.0

        price_pattern = r'(\d{1,3}(?:[.,]\d{3})+(?:,\d+)?|\d+)'
        
        # Generate AI keywords for exclude
        exclude_keywords = [
            'total', 'subtotal', 'sub-total', 'grand total',
            'jumlah', 'amount', 'tagihan', 'bill',
            'tax', 'pajak', 'ppn', 'vat', 'gst', 'pb1',
            'service', 'charge', 'layanan', 'biaya', 'gratuity', 'tip',
            'tunai', 'cash', 'kembali', 'change', 'kembalian',
            'bayar', 'paid', 'payment', 'tender', 'balance', 'sisa', 'due',
            'debit', 'credit', 'kredit', 'card', 'kartu', 'visa', 'master',
            'diskon', 'discount', 'disc', 'rounding', 'pembulatan'
        ]
        # Cek line by line
        for i, text in enumerate(text_list):
            clean_text = text.strip()
            
            match = re.search(price_pattern, clean_text)
            
            if match:
                price_str = match.group(0)
                try:
                    price_val = self._convert_price_str_to_float(price_str)
                except ValueError:
                    continue

                
                possible_name = clean_text.replace(price_str, "").replace("Rp", "").strip()
                
                if len(possible_name) > 2:
                    item_name = possible_name
                elif i > 0:
                    item_name = text_list[i-1].strip()
                else:
                    item_name = "Unknown Item"

                if not any(k in item_name.lower() for k in exclude_keywords):
                    new_item = ItemData(
                        name=item_name,
                        count=1,
                        total_price=price_val
                    )
                    items.append(new_item)
                    total_accumulated += price_val

        return ReceiptData(items={it.id: it for it in items}, total=total_accumulated)

    def _convert_price_str_to_float(self, price_str: str) -> float:
        """Helper to cleanup price string."""
        clean = price_str.lower().replace("rp", "").replace(".", "").replace(",", "").strip()
        return float(clean)