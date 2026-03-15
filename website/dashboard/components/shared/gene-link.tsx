import Link from "next/link";

export default function GeneLink({ gene }: { gene: string }) {
  return (
    <Link
      href={`/genes/${gene.toUpperCase()}`}
      className="gene-name"
      style={{ textDecoration: "none" }}
    >
      {gene.toUpperCase()}
    </Link>
  );
}
