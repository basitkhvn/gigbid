import "./globals.css";
import Shell from "@/components/Shell";
export const metadata = { title: "GigBid", description: "Multi-agent freelancer copilot" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1" /></head><body><Shell>{children}</Shell></body></html>);
}
