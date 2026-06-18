//
//  FeedView.swift
//  SummerSchoolProject
//

import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Лента")
                .task { await viewModel.load() }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingView()
        case .loaded(let posts):
            List {
                if viewModel.isOffline {
                    OfflineBadge()
                        .listRowInsets(EdgeInsets())
                        .listRowSeparator(.hidden)
                }
                ForEach(posts) { post in
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
            }
        }
        .padding(.vertical, 4)
    }
}
