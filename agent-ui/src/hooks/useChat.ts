/**
 * Chat hook — sends a message via `POST /api/v1/chat` and invalidates the
 * conversation list so the sidebar reflects any newly created conversation.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { chatApi } from "../api/chat";
import { queryKeys } from "../lib/queryClient";
import type { ChatRequest } from "../types/chat";

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChatRequest) => chatApi.send(payload),
    onSuccess: (data) => {
      // A brand-new conversation now exists; refresh the sidebar.
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({
        queryKey: queryKeys.conversationMessages(data.conversation_id),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.usage });
    },
  });
}
