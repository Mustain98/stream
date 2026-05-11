type PaymentRequiredOverlayProps = {
  priceAmount: number;
  currency: string;
  isPaying: boolean;
  onPay: () => void;
};

function formatPrice(amount: number, currency: string) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  } catch {
    return `${amount} ${currency.toUpperCase()}`;
  }
}

export function PaymentRequiredOverlay({
  priceAmount,
  currency,
  isPaying,
  onPay,
}: PaymentRequiredOverlayProps) {
  return (
    <div className="payment-overlay">
      <div className="payment-card">
        <p className="eyebrow">Payment required</p>
        <h2>Continue watching this stream</h2>
        <p className="muted">
          Pay {formatPrice(priceAmount, currency)} to unlock the full live stream.
        </p>

        <button className="primary-button" disabled={isPaying} onClick={onPay} type="button">
          {isPaying ? "Opening checkout..." : "Pay and continue"}
        </button>
      </div>
    </div>
  );
}