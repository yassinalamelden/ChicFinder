# Issue #3: Initialize Next.js "T3-Lite" Base Architecture

**Assignees:** @Gendy, @Nour  
**Labels:** `frontend`, `infrastructure`, `slice-1`, `high-priority`  
**Milestone:** MVP Web UI

---

## 🎯 Description

We are building a consumer-facing web interface for ChicFinder. We need to bootstrap a modern React application that will eventually communicate with Moamen's FastAPI backend.

---

## 📋 Tasks

- [ ] Create a new directory named `web_frontend/` in the project root.

- [ ] Initialize a Next.js App Router project with TypeScript and Tailwind CSS.

- [ ] Install `shadcn/ui` and initialize the base theme (keep the styling minimal/chic).

- [ ] Create the strict TypeScript interface `ChicFinderResult` in `web_frontend/types/api.ts` to exactly mirror the FastAPI backend schema.

### Contract / Mock Interface (Save in `types/api.ts`)

```typescript
// This is the strict contract. If the backend changes this, the build fails.
export interface ChicFinderResult {
  image_id: string;
  similarity_score: number;

  // Slice 3 Metadata (Nullable/Optional for safety)
  brand?: string | null;
  price_egp?: number | null;
  product_url?: string | null;
  store_location?: string | null;
  availability_egypt: boolean;
}

export interface SearchResponse {
  results: ChicFinderResult[];
  processing_time_ms: number;
}

export interface SearchRequest {
  image_base64: string;
  top_k: number;
}
```

---

## 📝 Acceptance Criteria

- [ ] Project runs successfully on `localhost:3000`.
- [ ] TypeScript interfaces are defined and committed exactly as shown above.
- [ ] No backend logic (Python/FastAPI) is touched in this PR.

---

## 📁 Key Files to Create

```
web_frontend/
├── types/
│   └── api.ts              # Strict TypeScript contract (ChicFinderResult, SearchResponse, SearchRequest)
├── app/
│   └── page.tsx            # Main page (Next.js App Router)
├── components/             # shadcn/ui components
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 🔗 Dependencies & Integration

### Depends On
- None — frontend architecture can be bootstrapped independently

### Coordinates With
- **Gendy's Issue #2** — FastAPI backend schema must match `ChicFinderResult` interface
- **Moamen's Slice 2 integration** — `SearchResponse` and `SearchRequest` must align with backend API contracts

---

## 💡 Implementation Tips

1. Use `npx create-next-app@latest web_frontend --typescript --tailwind --app` to bootstrap
2. Use `npx shadcn@latest init` inside `web_frontend/` to set up the component library
3. Keep Tailwind configuration minimal — chic, clean aesthetic
4. The `availability_egypt` field is required (non-optional) as it drives the Egypt market filter (Slice 3)
