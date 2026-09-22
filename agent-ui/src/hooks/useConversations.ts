/**
 * Conversation hooks — list, messages and delete.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { conversationsApi } from "../api/chat";
import { queryKeys } from "../lib/queryClient";

const DEFAULT_PAGE_SIZE = 50;

export function useConversations(pageSize = DEFAULT_PAGE_SIZE) {
  return useQuery({
    queryKey: queryKeys.conversations(1, pageSize),
    queryFn: () => conversationsApi.list({ page: 1, page_size: pageSize }),
  });
}

export function useConversationMessages(conversationId: string | null) {
  return useQuery({
    queryKey: queryKeys.conversationMessages(conversationId ?? "none"),
    queryFn: () =>
      conversationsApi.messages(conversationId as string, {
        page: 1,
        page_size: 100,
      }),
    enabled: conversationId !== null,
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) =>
      conversationsApi.remove(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
