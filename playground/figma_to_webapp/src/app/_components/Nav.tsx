import Link from "next/link";

export default function Nav() {
  return (
    <nav className="w-full border-b bg-white/70 backdrop-blur sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-12 flex items-center gap-2">
        <Link href="/" className="px-3 py-2 rounded hover:bg-gray-100">home</Link>
        <Link href="/page-1" className="px-3 py-2 rounded hover:bg-gray-100">page-1</Link>
        <Link href="/page-2" className="px-3 py-2 rounded hover:bg-gray-100">page-2</Link>
      </div>
    </nav>
  );
}
