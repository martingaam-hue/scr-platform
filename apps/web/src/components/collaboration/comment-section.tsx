"use client";

import React, { useState } from "react";
import {
  MessageSquare,
  Pencil,
  Trash2,
  CheckCircle,
  Reply,
  X,
} from "lucide-react";
import { Avatar, Badge, Button, cn, EmptyState } from "@scr/ui";
import {
  useComments,
  useCreateComment,
  useEditComment,
  useDeleteComment,
  useResolveComment,
  timeAgo,
  type CommentResponse,
} from "@/lib/collaboration";

interface CommentSectionProps {
  entityType: string;
  entityId: string;
  currentUserId?: string;
}

export function CommentSection({
  entityType,
  entityId,
  currentUserId,
}: CommentSectionProps) {
  const { data, isLoading } = useComments(entityType, entityId);
  const createComment = useCreateComment();
  const [newContent, setNewContent] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    createComment.mutate(
      {
        entity_type: entityType,
        entity_id: entityId,
        content: newContent,
      },
      { onSuccess: () => setNewContent("") }
    );
  };

  return (
    <div className="space-y-4">
      {/* New comment form */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="Add a comment... Use @name to mention someone"
          className="w-full resize-none rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 placeholder-neutral-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100 dark:placeholder-neutral-500"
          rows={3}
        />
        <div className="flex justify-end">
          <Button
            type="submit"
            size="sm"
            disabled={!newContent.trim() || createComment.isPending}
          >
            {createComment.isPending ? "Posting..." : "Comment"}
          </Button>
        </div>
      </form>

      {/* Comments list */}
      {isLoading ? (
        <div className="py-8 text-center text-sm text-neutral-400">
          Loading comments...
        </div>
      ) : !data?.items.length ? (
        <EmptyState
          icon={<MessageSquare className="h-8 w-8" />}
          title="No comments yet"
          description="Be the first to comment"
        />
      ) : (
        <div className="space-y-4">
          {data.items.map((comment) => (
            <CommentThread
              key={comment.id}
              comment={comment}
              entityType={entityType}
              entityId={entityId}
              currentUserId={currentUserId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentThread({
  comment,
  entityType,
  entityId,
  currentUserId,
}: {
  comment: CommentResponse;
  entityType: string;
  entityId: string;
  currentUserId?: string;
}) {
  return (
    <div className="space-y-3">
      <CommentItem
        comment={comment}
        entityType={entityType}
        entityId={entityId}
        currentUserId={currentUserId}
        isReply={false}
      />
      {comment.replies.length > 0 && (
        <div className="ml-10 space-y-3 border-l-2 border-neutral-100 pl-4 dark:border-neutral-800">
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              entityType={entityType}
              entityId={entityId}
              currentUserId={currentUserId}
              isReply
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentItem({
  comment,
  entityType,
  entityId,
  currentUserId,
  isReply,
}: {
  comment: CommentResponse;
  entityType: string;
  entityId: string;
  currentUserId?: string;
  isReply: boolean;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [isReplying, setIsReplying] = useState(false);
  const [replyContent, setReplyContent] = useState("");

  const editComment = useEditComment();
  const deleteComment = useDeleteComment();
  const resolveComment = useResolveComment();
  const createComment = useCreateComment();

  const isAuthor = currentUserId === comment.user_id;
  const isDeleted = comment.content === "[deleted]";

  const handleEdit = () => {
    editComment.mutate(
      {
        commentId: comment.id,
        content: editContent,
        entityType,
        entityId,
      },
      { onSuccess: () => setIsEditing(false) }
    );
  };

  const handleDelete = () => {
    if (confirm("Delete this comment?")) {
      deleteComment.mutate({ commentId: comment.id, entityType, entityId });
    }
  };

  const handleReply = () => {
    if (!replyContent.trim()) return;
    createComment.mutate(
      {
        entity_type: entityType,
        entity_id: entityId,
        content: replyContent,
        parent_comment_id: comment.id,
      },
      {
        onSuccess: () => {
          setReplyContent("");
          setIsReplying(false);
        },
      }
    );
  };

  return (
    <div className="flex gap-3">
      <Avatar
        alt={comment.author.full_name}
        src={comment.author.avatar_url ?? undefined}
        size="sm"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            {comment.author.full_name}
          </span>
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            {timeAgo(comment.created_at)}
          </span>
          {comment.is_resolved && (
            <Badge variant="success" className="text-xs">
              Resolved
            </Badge>
          )}
        </div>

        {isEditing ? (
          <div className="mt-1 space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full resize-none rounded-md border border-neutral-200 bg-white px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              rows={2}
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleEdit} disabled={editComment.isPending}>
                Save
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <p
            className={cn(
              "mt-0.5 text-sm",
              isDeleted
                ? "italic text-neutral-400 dark:text-neutral-500"
                : "text-neutral-700 dark:text-neutral-300"
            )}
          >
            {comment.content}
          </p>
        )}

        {/* Actions */}
        {!isDeleted && !isEditing && (
          <div className="mt-1 flex items-center gap-3">
            {!isReply && (
              <button
                onClick={() => setIsReplying(!isReplying)}
                className="flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <Reply className="h-3 w-3" />
                Reply
              </button>
            )}
            {isAuthor && (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <Pencil className="h-3 w-3" />
                Edit
              </button>
            )}
            <button
              onClick={handleDelete}
              className="flex items-center gap-1 text-xs text-neutral-400 hover:text-red-500"
            >
              <Trash2 className="h-3 w-3" />
              Delete
            </button>
            <button
              onClick={() =>
                resolveComment.mutate({
                  commentId: comment.id,
                  entityType,
                  entityId,
                })
              }
              className={cn(
                "flex items-center gap-1 text-xs",
                comment.is_resolved
                  ? "text-green-500 hover:text-green-600"
                  : "text-neutral-400 hover:text-green-500"
              )}
            >
              <CheckCircle className="h-3 w-3" />
              {comment.is_resolved ? "Unresolve" : "Resolve"}
            </button>
          </div>
        )}

        {/* Reply form */}
        {isReplying && (
          <div className="mt-2 space-y-2">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              className="w-full resize-none rounded-md border border-neutral-200 bg-white px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              rows={2}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleReply}
                disabled={!replyContent.trim() || createComment.isPending}
              >
                Reply
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsReplying(false)}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
