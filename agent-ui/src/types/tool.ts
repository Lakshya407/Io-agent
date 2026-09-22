/**
 * Tool types — mirror `app/schemas/tool.py`.
 */

export type ToolType =
  | "search"
  | "knowledge"
  | "utility"
  | "development"
  | "analytics"
  | "media";

/** `ToolOut` — public tool configuration. */
export interface Tool {
  id: string;
  name: string;
  description: string;
  type: ToolType;
  configuration: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** `ToolCreate` — payload for POST /api/v1/admin/tools. */
export interface ToolCreate {
  name: string;
  description: string;
  type?: ToolType;
  configuration?: Record<string, unknown>;
  is_active?: boolean;
}

/** `ToolUpdate` — payload for PUT /api/v1/admin/tools/{id}. */
export interface ToolUpdate {
  name?: string;
  description?: string;
  type?: ToolType;
  configuration?: Record<string, unknown>;
}

/** `ToolStatusUpdate` — payload for PATCH .../tools/{id}/status. */
export interface ToolStatusUpdate {
  is_active: boolean;
}
