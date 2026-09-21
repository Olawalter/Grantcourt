# PriceWire contract (excerpt)

class PriceWire(gl.Contract):
    price: str

    @gl.public.write
    def refresh(self) -> None:
        def fetch():
            return gl.nondet.web.get(PRICE_API).body.decode()
        self.price = gl.eq_principle.strict_eq(fetch)
