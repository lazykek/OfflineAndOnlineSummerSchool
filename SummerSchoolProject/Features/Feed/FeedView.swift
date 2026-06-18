//
//  FeedView.swift
//  SummerSchoolProject
//

import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()
    @EnvironmentObject private var outboxStore: OutboxStore
    @EnvironmentObject private var monitor: NetworkMonitor

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Лента")
                .task { await viewModel.load() }
                .toolbar {
                    if outboxStore.pendingCount > 0 {
                        ToolbarItem(placement: .topBarTrailing) {
                            OutboxBadge(count: outboxStore.pendingCount)
                        }
                    }
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingView()
        case .loaded(let posts):
            VStack(spacing: 0) {
                CacheBadge(dataSource: viewModel.dataSource)
                if !monitor.isOnline { OfflineBadge() }
                List(posts) { post in
                    postRow(post)
                }
            }
            .listStyle(.plain)
            .refreshable { await viewModel.load() }
        case .failed(let error):
            ErrorStateView(error: error) {
                Task { await viewModel.load() }
            }
        }
    }

    private func postRow(_ post: Post) -> some View {
        HStack(alignment: .top, spacing: 12) {
            CachedAsyncImage(url: post.imageURL)
                .frame(width: 100, height: 60)
                .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 4) {
                Text(post.title)
                    .font(.headline)
                Text(post.body)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                LikeButton(postID: post.id)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - LikeButton

private struct LikeButton: View {
    let postID: Int

    @EnvironmentObject private var processor: OutboxProcessor
    @EnvironmentObject private var outboxStore: OutboxStore

    @State private var liked = false

    private var isPending: Bool {
        outboxStore.items.contains {
            if case .likePost(let id) = $0.action, id == postID {
                return $0.status == .pending || $0.status == .inFlight
            }
            return false
        }
    }

    var body: some View {
        Button {
            guard !liked else { return }
            liked = true
            processor.enqueue(.likePost(postID: postID))
        } label: {
            HStack(spacing: 4) {
                Image(systemName: liked ? "heart.fill" : "heart")
                    .foregroundStyle(liked ? Color.red : Color.secondary)
                if isPending {
                    Text("· ожидает отправки")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                }
            }
            .font(.subheadline)
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.15), value: liked)
    }
}

// MARK: - OutboxBadge

private struct OutboxBadge: View {
    let count: Int
    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: "tray.and.arrow.up")
            Text("\(count)")
        }
        .font(.caption.bold())
        .foregroundStyle(.orange)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.orange.opacity(0.15), in: Capsule())
    }
}
