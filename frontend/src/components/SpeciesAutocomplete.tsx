// FloraCodex-backed species autocomplete. Selecting a hit fills species name,
// scientific name and the FloraCodex pid; free typing keeps it user-supplied.

import { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';

import { useSpeciesSearch } from '../api/hooks/useSpecies';
import type { SpeciesSearchResult } from '../api/types';

interface SpeciesAutocompleteProps {
  value: string;
  onChange: (speciesName: string) => void;
  onSelect: (species: SpeciesSearchResult) => void;
}

export function SpeciesAutocomplete({ value, onChange, onSelect }: SpeciesAutocompleteProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<number>(undefined);
  const { data: results = [] } = useSpeciesSearch(query);

  useEffect(() => () => window.clearTimeout(debounceRef.current), []);

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
        <input
          className="input-base pl-9"
          placeholder="Search species or type freely"
          value={value}
          onChange={(event) => {
            const next = event.target.value;
            onChange(next);
            setOpen(true);
            window.clearTimeout(debounceRef.current);
            debounceRef.current = window.setTimeout(() => setQuery(next), 300);
          }}
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        />
      </div>
      {open && results.length > 0 && (
        <ul className="card absolute z-10 mt-1 max-h-56 w-full overflow-y-auto">
          {results.map((species) => (
            <li key={species.pid}>
              <button
                type="button"
                className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-emerald-50"
                onMouseDown={() => {
                  onSelect(species);
                  setOpen(false);
                }}
              >
                {species.image_url && (
                  <img src={species.image_url} alt="" className="h-8 w-8 rounded object-cover" />
                )}
                <span>
                  <span className="font-medium">{species.name}</span>
                  {species.scientific_name && (
                    <span className="ml-2 italic text-stone-500">{species.scientific_name}</span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
