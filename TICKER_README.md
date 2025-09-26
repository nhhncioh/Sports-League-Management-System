# Score Ticker — quick integration

1) Run the SQL at `backend/migrations/2025_09_25_add_ticker.sql`.
2) Mount the blueprint in Flask:

    from backend.routes.ticker import bp as ticker_bp
    app.register_blueprint(ticker_bp)

3) In your Next.js layout (e.g., `src/app/layout.tsx`) render the ticker:

    import TickerBar from "@/src/components/ticker/TickerBar";
    export default function RootLayout({ children }) {
      return (
        <html lang="en"><body>
          <TickerBar leagueId={process.env.NEXT_PUBLIC_LEAGUE_ID!} />
          {children}
        </body></html>
      );
    }

4) In the admin “Homepage Builder”, include `AdminScoreTickerPanel` and pass the same `leagueId`.

5) Toggle ON, adjust colors/height/speed, and add items via Admin or the sample script.
