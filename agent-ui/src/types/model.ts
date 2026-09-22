/**
 * Model types — mirror `app/schemas/model.py`.
 */

export type ModelProvider = "openai" | "anthropic" | "ollama" | "custom";
export type ModelType = "chat" | "code" | "embedding";

/** `ModelOut` — public model configuration. */
export interface Model {
  id: string;
  name: string;
  provider: ModelProvider;
  model_identifier: string;
  model_type: ModelType;
  is_active: boolean;
  is_default: boolean;
  max_tokens: number;
  temperature: number;
  /** Local Ollama availability (null = unknown / non-Ollama). */
  available?: boolean | null;
  created_at: string;
  updated_at: string;
}

/** `ModelCreate` — payload for POST /api/v1/admin/models. */
export interface ModelCreate {
  name: string;
  provider?: ModelProvider;
  model_identifier: string;
  model_type?: ModelType;
  is_active?: boolean;
  is_default?: boolean;
  max_tokens?: number;
  temperature?: number;
}

/** `ModelUpdate` — payload for PUT /api/v1/admin/models/{id}. */
export interface ModelUpdate {
  name?: string;
  provider?: ModelProvider;
  model_identifier?: string;
  model_type?: ModelType;
  is_default?: boolean;
  max_tokens?: number;
  temperature?: number;
}

/** `ModelStatusUpdate` — payload for PATCH .../models/{id}/status. */
export interface ModelStatusUpdate {
  is_active: boolean;
}
