"""Collect actual existing campaign records later; no fixture or worker is run."""


def collect_existing(*, identifier, cases, runtime_expectations, selected_job_ids,
                     git_revision, plan_sha256, cluster_results_root,
                     copied_results_root, collection_budgets):
    from h2physics.cluster_evidence import CampaignExpectation, collect_campaign_evidence

    expectation = CampaignExpectation(
        identifier=identifier,
        cases=tuple(cases),
        runtimes=runtime_expectations,
        job_ids_by_case=selected_job_ids,
        revision=git_revision,
        plan_sha256=plan_sha256,
        cluster_results_root=cluster_results_root,
    )
    return collect_campaign_evidence(expectation, copied_results_root, budgets=collection_budgets)
