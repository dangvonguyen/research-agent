import type { components } from "@/shared/api/openapi.gen"

type Paper = components["schemas"]["Paper"];       

interface SearchResultCardProps {
  paper: Paper;
  onClick?: () => void;
}

const SearchResultCard = ({ paper, onClick }: SearchResultCardProps) => {
  const { title, authors, year, sections } = paper;

  const abstract = sections?.abstract?.content;

    // Cắt abstract lấy khoảng 10 từ đầu tiên
  const truncatedAbstract = abstract
    ? abstract.split(/\s+/).slice(0, 15).join(" ") + "..."
    : null;

  return (
    <button
      onClick={onClick}
      className="bg-white border-none text-left w-full p-4 cursor-pointer rounded-lg shadow-md hover:shadow-lg hover:-translate-y-1 transition-transform"
    >
      <h3 className="text-lg mb-2">{title}</h3>

      <p className="text-sm text-gray-600 mb-1">
        <strong>Authors:</strong> {authors?.join(", ")}{" "}
        {year && (
          <>
            | <strong>Year:</strong> {year}
          </>
        )}
      </p>

      {truncatedAbstract && (
        <p className="text-sm text-gray-600">
          <strong>Abstract:</strong> {truncatedAbstract}
        </p>
      )}
    </button>
  );
};

export default SearchResultCard;
