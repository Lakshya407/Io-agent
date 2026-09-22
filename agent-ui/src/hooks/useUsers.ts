/**
 * User hooks — list (server-side pagination), update and delete.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "../api/users";
import { queryKeys } from "../lib/queryClient";
import type { PageParams } from "../types/common";
import type { UserAdminUpdate } from "../types/user";

const DEFAULT_PAGE_SIZE = 20;

export function useUsers(params: PageParams = {}) {
  const page = params.page ?? 1;
  const pageSize = params.page_size ?? DEFAULT_PAGE_SIZE;
  return useQuery({
    queryKey: queryKeys.users(page, pageSize),
    queryFn: () => usersApi.list({ page, page_size: pageSize }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: UserAdminUpdate }) =>
      usersApi.update(userId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => usersApi.remove(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "usage"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}
