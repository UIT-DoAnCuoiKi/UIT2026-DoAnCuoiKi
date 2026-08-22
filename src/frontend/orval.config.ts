import { defineConfig } from "orval";

// Sinh client TypeScript cộng hook React Query từ OpenAPI của backend.
// Input là file openapi.json đã lưu (chạy `npm run gen:api`), hoặc lấy trực
// tiếp từ backend đang chạy (`npm run gen:api:remote`).
export default defineConfig({
  parking: {
    input: "./openapi.json",
    output: {
      // Code sinh ra nằm riêng trong generated/ để clean:true không xoá nhầm
      // axios-instance.ts (mutator viết tay) ở src/api/.
      target: "src/api/generated/endpoints.ts",
      schemas: "src/api/generated/model",
      client: "react-query",
      mode: "tags-split",
      mock: false,
      clean: true,
      prettier: false,
      override: {
        mutator: { path: "./src/api/axios-instance.ts", name: "customInstance" },
        query: { useQuery: true, useMutation: true },
      },
    },
  },
});
