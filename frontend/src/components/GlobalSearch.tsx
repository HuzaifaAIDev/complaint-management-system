import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, FileText, MessageSquareWarning, User as UserIcon, Users } from "lucide-react";
import { globalSearch } from "../services/resourceService";
import { GlobalSearchResults } from "../types";

export default function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GlobalSearchResults | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<number | undefined>(undefined);
  // Guards against a slow earlier request overwriting the result of a
  // faster, more recent one (classic type-ahead race condition).
  const requestSeqRef = useRef(0);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    setSearchError(false);

    if (query.trim().length < 2) {
      setResults(null);
      setOpen(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    debounceRef.current = window.setTimeout(() => {
      const seq = ++requestSeqRef.current;
      globalSearch(query.trim())
        .then((res) => {
          if (seq !== requestSeqRef.current) return; // a newer request has since superseded this one
          setResults(res);
          setOpen(true);
        })
        .catch(() => {
          if (seq !== requestSeqRef.current) return;
          setResults(null);
          setSearchError(true);
          setOpen(true);
        })
        .finally(() => {
          if (seq === requestSeqRef.current) setLoading(false);
        });
    }, 300);
    return () => window.clearTimeout(debounceRef.current);
  }, [query]);

  const goTo = (path: string) => {
    navigate(path);
    setOpen(false);
    setQuery("");
    setResults(null);
  };

  const hasResults = results && (
    results.requests.length || results.complaints.length || results.customers.length || results.users.length
  );

  return (
    <div className="global-search" ref={containerRef}>
      <Search size={16} className="global-search-icon" />
      <input
        type="text"
        placeholder="Search requests, complaints, customers..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => query.trim().length >= 2 && setOpen(true)}
        aria-label="Global search"
      />
      {open && (
        <div className="global-search-results" role="listbox">
          {loading && <div className="gsr-empty">Searching...</div>}
          {!loading && searchError && <div className="gsr-empty">Search is temporarily unavailable. Please try again.</div>}
          {!loading && !searchError && !hasResults && <div className="gsr-empty">No matches for "{query}"</div>}

          {!loading && !searchError && results && results.requests.length > 0 && (
            <div className="gsr-group">
              <div className="gsr-group-label">Requests</div>
              {results.requests.map((r) => (
                <button key={r.id} className="gsr-item" onClick={() => goTo(`/requests/${r.id}`)}>
                  <FileText size={14} />
                  <span className="gsr-ref">{r.reference_number}</span>
                  <span className="gsr-desc">{r.description}</span>
                </button>
              ))}
            </div>
          )}

          {!loading && results && results.complaints.length > 0 && (
            <div className="gsr-group">
              <div className="gsr-group-label">Complaints</div>
              {results.complaints.map((c) => (
                <button key={c.id} className="gsr-item" onClick={() => goTo(`/complaints/${c.id}`)}>
                  <MessageSquareWarning size={14} />
                  <span className="gsr-ref">{c.reference_number}</span>
                  <span className="gsr-desc">{c.description}</span>
                </button>
              ))}
            </div>
          )}

          {!loading && results && results.customers.length > 0 && (
            <div className="gsr-group">
              <div className="gsr-group-label">Customers</div>
              {results.customers.map((c) => (
                <button key={c.id} className="gsr-item" onClick={() => goTo(`/customers/${c.id}`)}>
                  <UserIcon size={14} />
                  <span className="gsr-ref">{c.full_name}</span>
                  <span className="gsr-desc">{c.email}</span>
                </button>
              ))}
            </div>
          )}

          {!loading && results && results.users.length > 0 && (
            <div className="gsr-group">
              <div className="gsr-group-label">Users</div>
              {results.users.map((u) => (
                <div key={u.id} className="gsr-item gsr-item-static">
                  <Users size={14} />
                  <span className="gsr-ref">{u.name}</span>
                  <span className="gsr-desc">{u.email} · {u.role}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
