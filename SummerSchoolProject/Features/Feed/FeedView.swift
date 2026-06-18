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
            List(posts) { post in
                VStack(alignment: .leading, spacing: 4) {
                    Text(post.title)
                        .font(.headline)
                    Text(post.body)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            }
            .listStyle(.plain)
            .refreshable { await viewModel.load() }
        case .failed(let error):
            ErrorStateView(error: error) {
                Task { await viewModel.load() }
            }
        }
    }
}
