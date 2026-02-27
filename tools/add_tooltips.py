#!/usr/bin/env python3
"""Add data-tooltip attributes to all resource cards in resources.html."""

import re
import html

# Map of resource h3 text -> tooltip description
# Each tooltip provides additional context beyond the visible card description
TOOLTIPS = {
    # === CTF Challenges & Vulnerable Environments ===
    "OWASP EKS Goat": "Covers RBAC misconfigurations, overly permissive IAM roles, container escapes, and lateral movement in EKS. Each lab includes both attack and defense perspectives. Free and open source — requires an AWS account with EKS permissions to deploy.",
    "Kubernetes Goat": "Created by Madhu Akula, this project includes 20+ scenarios covering container runtime exploits, SSRF in cloud metadata, and RBAC misconfigurations. Ships with a guided workbook and can run on any major cloud or locally via K3S.",
    "Kubecon NA 2019 CTF": "Originally developed for the KubeCon 2019 conference, this GCP-based CTF walks you through realistic Kubernetes attack and defense scenarios. Free to deploy in your own GCP account — ideal for workshop-style learning.",
    "OWASP Wrong Secrets": "Features 40+ challenges covering hardcoded secrets, cloud metadata abuse, and vault misconfigurations across AWS, GCP, and Azure. Runs locally via Docker or in the cloud. Great for developers learning secure secrets handling.",
    "CloudGoat": "Built by Rhino Security Labs, it offers 15+ scenario-based attack paths covering IAM privilege escalation, Lambda exploitation, and S3 misconfigurations. Each scenario deploys real AWS resources and includes detailed walkthrough documentation.",
    "FLAWS": "Created by Scott Piper, this progressive challenge teaches S3 bucket misconfigurations, EC2 metadata abuse, and IAM policy flaws through six escalating levels. No AWS account needed — everything runs on the challenge website itself.",
    "FLAWS 2": "Builds on the original FLAWS with an attacker and defender path. Covers container credential theft, Cognito misconfigurations, and additional AWS-specific attack vectors. No account required — hosted challenges you can start immediately.",
    "Wiz EKS Cluster Games": "A browser-based CTF where you start inside a vulnerable EKS pod and must find flags by exploiting misconfigurations. Features a global leaderboard and progressive difficulty. Requires free registration to track your progress.",
    "Wiz Big IAM Challenge": "Six progressively harder challenges focused on AWS IAM policy misconfigurations, privilege escalation, and trust boundary exploitation. Browser-based with no AWS account required — ideal for learning IAM security fundamentals.",
    "Wiz K8s LAN Party": "Five challenges exploring Kubernetes network security including DNS misconfigurations, service mesh bypass, and cross-namespace attacks. Browser-based with a global leaderboard. Tests skills in network policy and pod security.",
    "Wiz CTF Portal": "Aggregates all Wiz CTFs (EKS Cluster Games, Big IAM Challenge, K8s LAN Party, and more) in one place. Track your progress across challenges and compete on the global leaderboard. New challenges added periodically.",
    "Thunder CTF": "Developed at Carnegie Mellon, it deploys vulnerable GCP infrastructure you exploit to capture flags. Covers IAM misconfigurations, compute engine flaws, and cloud function exploits. Requires a GCP account — deploy costs are minimal.",
    "IAM Vulnerable": "Built by BishopFox, this Terraform project deploys 31 distinct IAM privilege escalation paths into your AWS account. Covers role chaining, policy manipulation, and cross-service pivoting. Pairs well with the CloudFox enumeration tool.",
    "CloudFoxable": "Companion project to CloudFox from BishopFox. Deploys vulnerable AWS scenarios via Terraform that you then enumerate and exploit using CloudFox. Teaches real-world cloud penetration testing methodology step by step.",
    "BadZure": "Deploys a deliberately vulnerable Azure and Entra ID environment via Terraform. Covers identity-based attacks, privilege escalation through app registrations, and service principal abuse. Requires an Azure subscription to deploy.",
    "AIGoat": "From Orca Security Research, this Terraform-based project deploys a vulnerable AI/ML pipeline in AWS. Covers model poisoning, insecure model endpoints, and data exfiltration through ML infrastructure. Requires an AWS account.",
    "CNAPPGoat": "Built by Tenable, it deploys vulnerable infrastructure across AWS, Azure, and GCP to test CNAPP tool effectiveness. Useful for benchmarking security tooling against known misconfigurations across multiple cloud providers.",
    "CICDont": "Deploys a vulnerable CI/CD pipeline using GitHub Actions, Jenkins, and ArgoCD. Covers secrets exposure in pipelines, dependency confusion, and build process manipulation. Great for DevSecOps engineers learning pipeline security.",
    "Bust a Kube": "Provides downloadable VMware virtual machines with vulnerable Kubernetes clusters. Practice container escapes, privilege escalation, and cluster compromise in a fully offline local environment. No cloud account needed.",
    "Kube Security Lab": "Uses Docker, Ansible, and Kind to create 14 different vulnerable Kubernetes cluster configurations locally. Each cluster targets specific misconfigurations like exposed dashboards, permissive RBAC, and insecure defaults.",
    "Blue Team Labs": "Azure Sentinel detection rules mapped to MITRE ATT&CK techniques. Practice building detections, writing KQL queries, and tuning alerts for cloud-specific attack patterns. Ideal for SOC analysts and detection engineers.",

    # === Hands-On Labs & Training Platforms ===
    "Hack The Box BlackSky": "Enterprise-grade cloud security labs with multi-stage attack chains across AWS, Azure, and GCP. Completing paths earns industry-recognized Cloud Security Specialist credentials. Paid subscription required.",
    "Cybr Free AWS Labs": "One-click lab deployments in a sandboxed AWS environment — no personal AWS account needed. Labs cover IAM, S3, EC2 security, and more. Completely free with new labs added regularly by the community.",
    "Digital Cloud Training Challenge Labs": "Labs auto-validate your work and provide scoring. Covers Solutions Architect, Security Specialty, and Azure Administrator paths. Subscription-based with a free tier for sampling labs.",
    "AWS Well-Architected Security Labs": "Official AWS labs organized by the Well-Architected Framework security pillar. Covers identity management, detection, infrastructure protection, and incident response. Free — uses your own AWS account.",
    "Awesome CloudSec Labs": "Community-maintained GitHub list aggregating free cloud security labs, workshops, CTFs, and research environments. Regularly updated with new resources. A great meta-resource for discovering hands-on content.",
    "Immersive Labs": "Enterprise platform used by Fortune 500 companies for cybersecurity readiness. Content maps to major frameworks and provides metrics for team capability assessment. Primarily B2B with organizational licensing.",
    "SecureFlag GCP Labs": "Hands-on labs specifically for GCP security covering IAM configuration, VPC networking, encryption key management, and API security. Addresses a gap in GCP-focused training content that most platforms lack.",
    "Pwned Labs": "Scenario-based labs simulating real-world breach situations in AWS and Azure. Assume-breach methodology teaches post-exploitation and lateral movement. Offers professional certifications upon completion. Paid platform.",
    "TryHackMe": "Beginner-friendly gamified platform with structured learning paths for cloud security. Browser-based attack boxes mean no local setup required. Free tier available with limited daily access to rooms.",
    "A Cloud Guru": "Now part of Pluralsight, it offers sandbox cloud environments for hands-on practice. Strong AWS coverage with growing Azure and GCP content. Subscription-based with team licensing available.",
    "CBT Nuggets": "Video-based training with virtual labs and practice exams for cloud security certifications. Known for engaging instructor-led content. Subscription-based — commonly provided through employer training budgets.",
    "Udemy Courses": "Marketplace model means quality varies by instructor — check ratings and reviews carefully. Frequent sales bring courses to $10-15. Popular cloud security instructors include Stephane Maarek and Neal Davis.",
    "Amazon EKS Workshop": "Official AWS workshop covering EKS cluster setup, networking, security, and observability. Includes modules on pod security standards, network policies, and secrets management. Free to follow in your own account.",
    "The Homelab Almanac": "From the Taggart Institute, this guide walks you through building a security home lab with Proxmox, pfSense, and infrastructure-as-code. Covers network segmentation, logging, and monitoring. Completely free and self-paced.",
    "Cybersecurity Expert Roadmap": "Community-driven visual roadmap showing skills, tools, and certifications needed at each career level. Interactive and regularly updated. Covers both technical and soft skills needed for cloud security roles.",
    "SLAW: Security Lab a Week": "Rich Mogull of Securosis publishes bite-sized cloud security labs weekly. Each takes 15-30 minutes and focuses on a specific practical scenario. Free — great for maintaining skills with regular practice.",

    # === Security Tools & Platforms ===
    "AccuKnox CNAPP": "Built on open-source KubeArmor for runtime enforcement using eBPF and Linux Security Modules. Offers both SaaS and self-hosted deployment. Strong in Kubernetes-native workload protection with inline threat mitigation.",
    "Wiz CNAPP": "Pioneered the agentless cloud security model using snapshot-based scanning. Its Security Graph visualizes attack paths across multi-cloud environments. One of the fastest-growing cybersecurity companies, now part of Google Cloud.",
    "Sysdig Secure": "Built on the open-source Sysdig and Falco projects for deep system call visibility. Strong in container runtime security with eBPF-based monitoring. Offers both SaaS and on-premises deployment options.",
    "Orca Security": "Uses patented SideScanning technology to read cloud workload data from block storage snapshots without installing agents. Provides unified visibility across VMs, containers, and serverless. SaaS-only deployment model.",
    "Aikido Security": "Developer-first security platform that traces vulnerabilities from runtime detection back to the specific IaC source code. Combines nine security capabilities (CSPM, CWPP, SAST, DAST, SCA, and more) in a single interface.",
    "Fidelis Security Halo": "Differentiated by its lightweight 2MB microagent that self-installs without reboots. Supports both Windows and Linux workloads. Designed for organizations with strict performance requirements for agent-based security.",
    "Shodan": "Indexes billions of devices including cloud infrastructure, IoT, ICS/SCADA systems, and databases. Invaluable for discovering your organization's external attack surface. Free tier available with paid plans for advanced queries and monitoring.",
    "ZoomEye": "Chinese cyberspace search engine with strong coverage of Asian IP ranges. Useful for discovering exposed services that other scanners may miss. Offers both web interface and API access for automation.",
    "Binary Edge": "Scans the entire IPv4 space and provides attack surface data via API. Covers open ports, SSL certificates, vulnerabilities, and data leaks. Free tier with limited queries — paid plans for continuous monitoring.",
    "LeakIX": "Focuses specifically on exposed data and misconfigurations rather than general port scanning. Finds open databases, exposed S3 buckets, and unprotected admin panels. Free to search with results updated in near real-time.",
    "DNSDumpster": "Free web-based tool that maps DNS records, discovers subdomains, and visualizes domain relationships. Powered by HackerTarget.com. No account required — useful for quick reconnaissance during assessments.",
    "Security Trails": "Provides current and historical DNS data, WHOIS records, and associated domains. Useful for mapping an organization's full domain footprint. Free tier with limited searches — API available for automation.",
    "grep.app": "Searches over half a million public GitHub repositories instantly. Useful for finding exposed API keys, credentials, internal URLs, and configuration patterns in open-source code. Free to use with no account required.",
    "Dorksearch": "Simplifies Google dorking with pre-built search templates for finding exposed files, login pages, and misconfigurations. Useful for OSINT and external reconnaissance without needing to memorize complex search operators.",
    "Packet Storm": "One of the oldest security information archives, operating since 1998. Contains exploit code, advisories, whitepapers, and security tools. Valuable for researching vulnerabilities and understanding historical attack techniques.",
    "Exploit-DB": "Maintained by OffSec (creators of Kali Linux), this is the most authoritative public exploit archive. Includes verified exploits, shellcode, and Google dorks. Every exploit is tested and categorized by platform and type.",
    "CloudVulnDB": "Community-maintained database cataloging cloud-specific vulnerabilities and misconfigurations across AWS, Azure, GCP, and other providers. Useful for understanding cloud-specific risk beyond traditional CVEs.",
    "OWASP": "The definitive open-source resource for application security. Produces the OWASP Top 10, testing guides, and security cheat sheets. All resources are free and community-driven with 250+ local chapters worldwide.",
    "Cloud Katana": "From Rhino Security Labs, this tool automates cloud adversary emulation by executing attack techniques mapped to MITRE ATT&CK. Useful for testing detection rules and validating security controls in live cloud environments.",
    "ScoutSuite": "From NCC Group, this open-source tool generates comprehensive security reports for AWS, Azure, GCP, Oracle Cloud, and Alibaba Cloud. Runs locally using your credentials — no SaaS dependency. Widely used in audits.",
    "ReARM": "Manages and correlates SBOMs, SAST/DAST results, attestations, and other security artifacts at the release level. Open-source platform for maintaining a chain of evidence across your software supply chain.",
    "Saner CNAPP": "Integrates CSPM, CIEM, and CWPP with AI-driven anomaly detection and automated remediation workflows. Focuses on reducing alert fatigue through intelligent prioritization and contextual risk scoring.",
    "Datadog Cloud Security": "Extends Datadog's observability platform with CSPM, CWPP, and application security. Strong integration with existing Datadog APM and infrastructure monitoring. Ideal for teams already using Datadog for observability.",
    "Lacework Polygraph": "Uses unsupervised machine learning to baseline normal cloud behavior and detect anomalies without predefined rules. Acquired by Fortinet in 2023 — now part of the FortiCNAPP platform.",
    "SentinelOne Cloud": "Extends endpoint detection and response (EDR) capabilities to cloud workloads. Strong in runtime threat detection with autonomous response actions. Integrates with SentinelOne's broader XDR platform.",
    "Check Point CloudGuard": "Part of Check Point's consolidated security architecture. Covers CNAPP, WAF, DDoS protection, and API security. Leverages Check Point's ThreatCloud AI for real-time threat intelligence across cloud workloads.",
    "Sysdig Secure": "Container and Kubernetes security platform built on Falco for runtime threat detection. Provides deep container forensics with full system call capture. Strong in compliance reporting for PCI-DSS, SOC 2, and NIST.",
    "CrowdStrike Falcon Cloud": "Extends CrowdStrike's industry-leading threat intelligence to cloud environments. Focuses on identity-based attacks with continuous IAM assessment and least-privilege enforcement. Part of the broader Falcon platform.",
    "Orca Security": "Scans cloud workloads via snapshot analysis without deploying agents. Provides full-stack visibility covering VMs, containers, serverless, and Kubernetes. Unified platform addressing CSPM, CWPP, and CIEM needs.",
    "Palo Alto Prisma Cloud": "One of the most comprehensive CNAPPs covering code-to-cloud security. Includes CSPM, CWPP, CIEM, WAAS, and code security. Extensive compliance library and strong IaC scanning capabilities.",

    # === Certifications & Professional Development ===
    "CKS Certification": "Two-hour performance-based exam where you solve real Kubernetes security tasks in a live environment. Requires passing CKA first. Covers cluster hardening, system hardening, supply chain security, and runtime monitoring.",
    "Pwned Labs Professional Bootcamps": "Intensive bootcamps with hands-on labs targeting specific cloud providers: ACRTP for AWS, MCRTP for Azure/M365, and GCRTP for GCP. Each culminates in a certification exam with real-world scenario challenges.",
    "CSA Cloud Threat Modeling": "Self-paced training covering the CSA top 11 cloud threats and systematic threat modeling approaches. Teaches risk treatment methods specific to cloud architectures. Available through the CSA training portal.",
    "AWS Certified Cloud Practitioner": "Entry-level exam covering AWS cloud concepts, billing, security basics, and core services. 90 minutes, 65 questions, multiple choice. No prerequisites — recommended starting point for anyone new to AWS.",
    "AWS Solutions Architect Associate (SAA-C03)": "Covers designing secure, resilient architectures on AWS. Tests knowledge of IAM, VPC design, encryption, and compliance. 130 minutes, 65 questions. One of the most popular cloud certifications globally.",
    "AWS Solutions Architect Professional": "Advanced exam testing complex, multi-account AWS architectures. Covers advanced security patterns, disaster recovery, and cost optimization. 180 minutes, 75 questions. Requires deep hands-on AWS experience.",
    "Security Certification Roadmap": "Interactive chart mapping 400+ security certifications by domain and difficulty level. Covers cloud, offensive, defensive, management, and specialized certifications. Maintained by Paul Jerimy and updated regularly.",
    "ISC2 CCSP 2025": "Updated for 2025 with new domains covering zero trust architecture, DevSecOps, and cloud-native security. Requires 5 years of IT experience including 3 in security. Four-hour, 150-question exam. Globally recognized credential.",
    "CKS: Kubernetes Security": "Hands-on certification requiring live cluster tasks covering network policies, pod security, secrets encryption, and audit logging. Two-hour exam with a passing score of 67%. Requires active CKA certification.",
    "CSA CCSK v5": "Updated to version 5 covering modern cloud security including serverless, containers, and DevSecOps. Multiple-choice exam with no experience prerequisites. Often used as a stepping stone to the ISC2 CCSP certification.",
    "GIAC GCSA & GCLD": "GCSA focuses on cloud security automation with IaC, CI/CD security, and cloud-native tooling. GCLD covers cloud data security including encryption, DLP, and data governance. Both are proctored exams with practical focus.",
    "CompTIA Cloud+ 2025": "Vendor-neutral certification covering cloud security, deployment, and operations across hybrid environments. Updated for 2025 with expanded security domains. Performance-based and multiple-choice questions. DoD 8570 approved.",
    "Security Blue Team": "Offers BTL1 and BTL2 certifications focused on defensive security skills. Hands-on labs cover SIEM analysis, digital forensics, and incident response. Practical exam format with real-world scenarios. Growing industry recognition.",
    "WiCyS Mentorship Program": "Annual cohort-based program specifically supporting women in cybersecurity. Pairs mentees with senior professionals for 6-12 months of structured career development. Includes conference access and networking events.",
    "ISACA Mentorship Program": "Global program open to all ISACA members. Both mentors and mentees earn Continuing Professional Education (CPE) credits. Covers IT audit, cybersecurity, risk management, and governance career paths.",
    "Cyversity": "Nonprofit focused on increasing diversity in cybersecurity. Mentorship program pairs underrepresented professionals with established leaders. Also offers scholarships, training resources, and conference sponsorships.",
    "CyberSecurity Mentoring Hub": "Global program with both 1-on-1 mentoring and group sessions. Hosts regular webinars, networking events, and career workshops. Open to all experience levels from students to mid-career professionals.",
    "MentorCruise - Cybersecurity": "Paid mentorship marketplace where you choose a mentor based on their expertise and reviews. Sessions are typically weekly or bi-weekly. Mentors include security engineers, CISOs, and penetration testers.",
    "ISSA International": "The largest global nonprofit organization of security professionals. Local chapters host monthly meetings, conferences, and training events. Membership provides access to the ISSA Journal and career resources.",
    "Cloud Security Alliance Community": "Publishes foundational cloud security guidance including the CCM, STAR registry, and Security Guidance v5. Working groups cover topics from AI to zero trust. Membership includes access to research and events.",
    "Lateral Connect Mentoring": "Small-group mentorship model where 3-5 mentees work with one experienced professional over several months. Emphasizes collaborative problem-solving and peer learning alongside traditional mentorship.",
    "Blacks In Cybersecurity": "Annual conference and year-round mentorship program building a supportive community for Black professionals in cybersecurity. Covers technical skills, career strategy, and leadership development.",
    "MassCyberCenter Mentorship": "State-funded program based in Massachusetts connecting undergraduate students from diverse backgrounds with cybersecurity professionals. Structured program with defined milestones and career exploration activities.",
    "OWASP Community": "Join local chapter meetups for free — no OWASP membership required. Chapters host talks, workshops, and CTF events. Great way to network with application and cloud security professionals in your area.",
    "See Yourself in Cyber": "National Cybersecurity Alliance campaign during Cybersecurity Awareness Month (October). Provides resources for students exploring cybersecurity careers including scholarships, events, and mentorship connections.",
    "InfraGard": "Members receive FBI threat briefings, attend SIG (Special Interest Group) meetings, and access a secure communication portal. Background check required for membership. Chapters in all 50 US states.",
    "Leland - Cybersecurity Mentors": "Premium mentoring platform with vetted cybersecurity professionals from companies like Google, Microsoft, and CrowdStrike. One-on-one coaching for career transitions, interview prep, and skill development.",
    "The Triangle Net": "Community platform connecting aspiring cybersecurity professionals with internships, mentorships, and entry-level positions. Strong focus on bridging the gap between education and first security roles.",

    # === AI Security & LLM Protection ===
    "Tumeryk": "Provides automated red-teaming for cloud AI deployments. Simulates adversarial attacks against your infrastructure and generates AI-powered remediation recommendations. Useful for validating AI security posture before production.",
    "Lakera Guard": "Deployed as an API proxy between your application and the LLM. Scans prompts and responses in real-time with sub-50ms latency. Trained on millions of real-world attack examples. Enterprise-grade with SOC 2 compliance.",
    "NVIDIA Garak": "Named after the Star Trek character, it probes LLMs for hallucination, data leakage, prompt injection, and dozens of other vulnerability categories. Supports OpenAI, Hugging Face, and local model testing. Actively maintained.",
    "LLM Guard": "Provides both input and output scanners that run as middleware. Detects PII leakage, prompt injection, toxicity, and banned topics. Can be self-hosted for data sovereignty requirements. Over 2.5 million downloads.",
    "Rebuff AI": "Combines three detection layers: heuristic pattern matching, LLM-based semantic analysis, and canary token injection. Open-source from ProtectAI. Useful for building defense-in-depth against prompt injection attacks.",
    "CalypsoAI Moderator": "Enterprise-grade LLM security that works with any model provider (OpenAI, Anthropic, open-source). Provides real-time content moderation, data loss prevention, and compliance reporting. Used by government agencies.",
    "NeMo Guardrails": "Define conversational boundaries using Colang, a domain-specific language for LLM behavior rules. Supports topical rails, safety rails, and custom actions. Integrates with LangChain and other orchestration frameworks.",
    "Guardrails AI": "Lets you define output specifications as Pydantic models. Validates LLM outputs against structure, type, and content rules. Includes pre-built validators for common risks like PII disclosure and toxic content generation.",
    "Giskard AI Security": "Automated testing platform that generates adversarial test cases tailored to your specific domain. Detects prompt injection, data leakage, and factual inconsistencies. Integrates with CI/CD pipelines for continuous testing.",
    "LLMFuzzer": "Generates diverse adversarial inputs to test LLM API endpoints. Supports custom fuzzing strategies and can target specific vulnerability categories. Open-source and designed for integration into security testing workflows.",
    "Pynt LLM Security": "Analyzes actual API traffic to discover prompt injection vulnerabilities and insecure output handling. Works by instrumenting your application's LLM API calls rather than testing in isolation.",
    "BurpGPT": "Extends Burp Suite's web security testing capabilities with LLM-powered analysis. Automatically identifies complex vulnerabilities that rule-based scanners miss. Useful for security professionals already using Burp Suite.",
    "Lasso Security": "Enterprise platform providing threat modeling, vulnerability assessment, and continuous monitoring for LLM deployments. Covers both external attacks (prompt injection) and internal risks (data leakage, model theft).",
    "WhyLabs LLM Security": "Monitors LLM inputs and outputs in production for anomalous patterns indicating attacks. Provides dashboards for tracking prompt injection attempts, data loss events, and content policy violations over time.",
    "Protecto AI": "Focuses on privacy-preserving AI with a Privacy Vault that encrypts and anonymizes data before LLM processing. Ensures compliance with GDPR, CCPA, and HIPAA for healthcare and financial services AI deployments.",
    "Vigil": "Lightweight, early-stage prompt scanner designed for high-throughput environments. Validates prompts against configurable rules without requiring infrastructure changes. Good starting point for teams beginning LLM security.",
    "OpenAI Aardvark": "AI agent that monitors code commits for security vulnerabilities using LLM reasoning. Automatically generates explanations of security issues and suggests fixes. Represents the emerging category of AI-powered security agents.",
    "Microsoft PyRIT": "Microsoft's open-source red-teaming toolkit for systematically probing LLMs. Supports multi-turn attack scenarios, scoring rubrics, and automated result analysis. Used internally at Microsoft for AI safety testing.",
    "Constitutional AI": "Foundational research paper from Anthropic describing how to train AI systems using a set of principles (a constitution) rather than human feedback alone. Key reading for understanding modern AI alignment approaches.",
    "Alert AI Gateway": "Sits between applications and LLM providers as a security proxy. Enforces zero-trust policies, scans for vulnerabilities, and provides audit logging across the full AI development and deployment lifecycle.",
    "DeepEval": "Open-source evaluation framework using LLM-as-judge methodology. Tests for 14+ metrics including hallucination, bias, toxicity, and coherence. Integrates with pytest for automated testing in CI/CD pipelines.",
    "Nexos.ai Platform": "Unified governance platform combining an AI Gateway for traffic control, workspaces for team collaboration, guardrails for policy enforcement, and observability for monitoring LLM usage and security events.",
    "Granica AI Crunch": "Optimizes AI training data pipelines by detecting and removing PII, reducing data volume, and ensuring compliance. Particularly useful for organizations training or fine-tuning models on sensitive enterprise data.",
    "Mindgard AI": "Provides continuous AI security posture management similar to CSPM but for AI models. Automated threat detection, risk scoring, and remediation for deployed models. Published research on guardrail evasion techniques.",
    "DeepStrike AI Pentesting": "Specialized penetration testing services targeting AI systems. Tests include model inversion attacks, membership inference, prompt injection, and training data extraction. Provides detailed reports with remediation guidance.",
    "Hugging Face Model Cards": "Standardized documentation format for AI models covering intended use, limitations, biases, and evaluation results. Essential for responsible AI deployment and security review of third-party models.",
    "OWASP Top 10 for LLMs 2025": "The industry-standard reference for LLM security risks. Updated annually by hundreds of security experts. Essential reading for anyone building, deploying, or securing LLM-powered applications.",
    "OWASP Agentic AI Top 10 2026": "First comprehensive framework addressing security risks specific to autonomous AI agents. Covers tool poisoning, excessive autonomy, memory manipulation, and agentic manipulation attack patterns.",
    "Prompt Injection Guide": "Deep dive into the #1 ranked risk in the OWASP LLM Top 10. Covers direct injection, indirect injection via documents, and cross-plugin attacks. Includes detailed mitigation strategies and detection approaches.",
    "CSA Guardrails Guide": "Enterprise-focused guide covering architectural patterns for LLM guardrails including input validation, output filtering, DLP integration, and compliance monitoring. Written for security architects and CISOs.",
    "Bypassing LLM Guardrails Research": "Peer-reviewed academic paper demonstrating that invisible Unicode characters and adversarial prompts can bypass commercial guardrails with near-perfect success rates. Important for understanding current defense limitations.",
    "Wiz Research Blog": "Publishes detailed write-ups of real cloud security incidents and vulnerabilities discovered by Wiz researchers. Covers topics from cross-tenant exploits to supply chain attacks. High-quality, freely accessible content.",
    "CNAPPs Surge Report": "Industry analysis showing CNAPPs becoming a top-3 security investment priority. Covers how AI integration in CNAPPs is reducing alert fatigue and enabling faster incident response across organizations.",
    "LLM Security Guide": "Open-source GitHub repository aggregating LLM security resources, vulnerability taxonomies, tool comparisons, and mitigation strategies. Well-organized reference for security teams beginning their AI security journey.",
    "Datadog Guardrails Best Practices": "Practical engineering guide covering input sanitization, prompt template hardening, output filtering, and monitoring patterns for LLM applications. Includes code examples and architectural diagrams.",
    "Lakera Prompt Injection Guide": "Hands-on guide with real-world prompt injection examples, categorized by attack type. Covers direct, indirect, and multi-step injection techniques alongside specific defense implementations.",
    "Obsidian: Prompt Injection #1": "Data-driven analysis showing prompt injection appearing in 73% of production LLM deployments surveyed. Provides enterprise-specific mitigation strategies including network segmentation and privilege reduction.",
    "Confident AI: Ultimate Guardrails Guide": "Step-by-step implementation guide for building LLM guardrails using the LLM-as-judge pattern. Covers data leakage prevention, bias detection, and jailbreak resistance with code examples.",
    "Invicti: OWASP LLM Analysis": "Maps each OWASP LLM Top 10 risk to business impact scenarios and provides testing methodologies. Useful for translating technical LLM risks into language that business stakeholders understand.",
    "Qualys: OWASP 2025 Updates": "Detailed analysis of what changed between the 2024 and 2025 versions of the OWASP LLM Top 10. Highlights new entries like RAG vulnerabilities and vector/embedding weaknesses as emerging threat categories.",
    "EvidentlyAI: OWASP Testing": "Practical testing guide showing how to evaluate your Gen AI application against each OWASP LLM Top 10 risk. Includes risk assessment templates and adversarial testing scripts you can adapt.",
    "Strobes: Mitigation Playbook": "For each OWASP LLM Top 10 risk, provides specific technical controls, governance frameworks, and monitoring approaches. Designed as a ready-to-use playbook for security teams implementing LLM protections.",
    "Nexos.ai: Top 10 LLM Tools": "Side-by-side comparison of leading LLM security tools evaluated on detection accuracy, latency impact, enterprise features, and integration capabilities. Useful for teams evaluating tool purchases.",
    "Lakera: Top 12 LLM Tools": "Covers both open-source and commercial LLM security tools including vulnerability scanners, guardrail frameworks, and monitoring platforms. Each tool reviewed with strengths, limitations, and ideal use cases.",
    "Pynt: Essential LLM Tools": "Focused guide covering the minimum essential toolset for LLM security: prompt injection detection, data leakage prevention, output validation, and automated security testing. Good starting point for new teams.",
    "Protecto: Best LLM Tools 2025": "Comprehensive review evaluating LLM security tools across categories: testing, monitoring, compliance, and privacy. Includes pricing information and deployment complexity ratings for each tool.",
    "Obsidian: AI Pentesting Tools": "Reviews specialized tools for penetration testing AI systems including model probing, prompt fuzzing, and adversarial input generation. Aimed at security professionals expanding into AI security testing.",
    "Mindgard: Guardrail Evasion": "Original research demonstrating how invisible Unicode characters and carefully crafted adversarial prompts can evade major commercial guardrail products. Important for understanding the arms race in LLM defense.",
    "MDPI: Prompt Injection Review": "Peer-reviewed academic survey analyzing 45 research papers on prompt injection from 2023-2025. Proposes the PALADIN defense framework and identifies open research challenges in LLM security.",
    "DeepStrike: OWASP Deep Dive": "Detailed walkthrough of each OWASP LLM Top 10 vulnerability with realistic attack scenarios, business impact assessments, and specific remediation steps. Written for both technical and management audiences.",
    "AccuKnox: Monitoring Tools 2025": "Evaluates seven cloud security monitoring tools on real-time threat detection, runtime protection, compliance automation, and integration capabilities. Includes feature comparison tables.",
    "TechTarget: CNAPP vs CSPM": "Explains the evolution from standalone CSPM to consolidated CNAPP platforms. Provides decision criteria for when each approach is appropriate based on cloud maturity and security team capabilities.",
    "MD5 Decrypt": "Online database of pre-computed hash values for MD5, SHA-1, and other algorithms. Useful during security assessments for quickly identifying known password hashes. Free to use with no registration required.",
    "Who Posted What": "Specialized OSINT tool for searching public Facebook and Instagram posts by keyword, date range, and location. Commonly used in security investigations and social engineering assessments.",
    "CyberSources": "Community-curated GitHub repository organizing cybersecurity tools, learning resources, and reference materials into categories. Regularly updated by contributors. Good starting point for discovering new security resources.",
    "Terminal Trove": "Searchable directory of command-line tools for security, DevOps, and system administration. Each tool includes installation instructions, feature summaries, and platform compatibility. Useful for discovering niche CLI utilities.",
    "Schneier on Security": "Bruce Schneier is a renowned cryptographer and security technologist. His blog covers security policy, cryptography, surveillance, and emerging threats. Required reading for understanding the broader security landscape.",

    # === Job Search & Career Development ===
    "LinkedIn": "Beyond job listings, use LinkedIn for publishing security content, engaging with CISOs, and building thought leadership. Optimize your profile with cloud security keywords. Join groups like Cloud Security Alliance and ISACA.",
    "Dice": "Includes salary estimator tools and market analytics for cybersecurity roles. Advanced search filters let you target specific technologies (AWS, Azure, Kubernetes). Primarily focused on US-based technology positions.",
    "CyberSeek": "Funded by NICE (NIST) and CompTIA, it provides interactive heat maps showing cybersecurity job demand by US metro area. Career pathway tool maps certification requirements for different security roles.",
    "ClearanceJobs": "The largest job board for security-cleared professionals in the US. Requires an active or recent security clearance. Positions from defense contractors, intelligence agencies, and cleared commercial organizations.",
    "CyberSecJobs": "Niche board with strong federal and defense contractor presence. Many positions require security clearances. Smaller volume than general boards but higher relevance for cybersecurity-specific roles.",
    "CyberSN": "Offers free job posting and a matching algorithm that pairs candidates with roles based on skills rather than keywords. Covers all cybersecurity levels from entry to CISO. Includes salary benchmarking data.",
    "CareersinCyber": "Particularly strong for governance, risk management, and compliance (GRC) positions. Good coverage of audit, privacy, and policy roles in financial services and healthcare. UK and US focused.",
    "Glassdoor": "Use company reviews and salary reports to research potential employers before interviews. The interview experience section reveals common questions asked at specific companies. Free to use with optional premium tier.",
    "Indeed": "Aggregates listings from company websites, staffing agencies, and other job boards. Use Boolean search operators (AND, OR, NOT) and location filters for targeted results. Free resume posting and company research tools.",
    "USAJOBS": "Federal cybersecurity positions use the GS pay scale (GS-7 through GS-15 and SES). Applications require detailed resumes in federal format. Consider the Pathways program for entry-level and student positions.",
    "Hack The Box Careers": "Companies post positions specifically targeting candidates with HTB experience. Your platform rank, badges, and completed challenge history serve as demonstrated proof of technical skills to potential employers.",
    "Scale.jobs": "Uses AI to auto-apply to matching positions and optimize your resume for each application. Includes human support for interview preparation. Particularly useful for high-volume job searching in competitive markets.",
    "Wiz Cloud Security Jobs Board": "Curated cloud security positions from companies in the Wiz ecosystem and broader cloud security industry. Useful for finding roles at cloud-native companies with strong security cultures.",
    "Resume Worded": "AI-powered analyzer that scores your resume against ATS compatibility criteria. Provides line-by-line suggestions for improvement. Free tier offers limited scans — premium unlocks unlimited reviews and LinkedIn optimization.",
    "VisualCV": "Offers both traditional and visual resume formats with analytics showing who viewed your resume and for how long. Templates are designed for ATS compatibility. Free basic tier with premium customization options.",
    "Wozber": "Completely free resume builder with built-in ATS scanner that checks keyword matching against specific job descriptions. No watermarks or hidden fees. Good option for budget-conscious job seekers.",
    "Enhancv": "Offers cybersecurity-specific resume examples and templates with sections for certifications, projects, and technical skills. AI-powered content suggestions help frame accomplishments with impact metrics.",
    "Toptal Resume Review": "Expert-written guide covering current ATS trends, formatting best practices, and keyword optimization strategies for technical roles. Includes before-and-after resume examples for cybersecurity positions.",
    "Resumatic": "AI-powered platform that generates ATS-optimized resumes from your LinkedIn profile or existing resume. Includes role-specific templates for cybersecurity analysts, engineers, and architects.",
    "Teal HQ LinkedIn Guides": "Step-by-step guides for optimizing every section of your LinkedIn profile for cybersecurity roles. Covers headline formulas, summary templates, and skill endorsement strategies that attract recruiter attention.",
    "National Cybersecurity Alliance - Resume & LinkedIn Guide": "Written with input from technical recruiters at major cybersecurity companies. Covers common resume mistakes, how to showcase certifications, and LinkedIn networking strategies.",
    "LinkedIn Mentorship Program": "Includes the CoachIn initiative specifically supporting women in technology. Structured mentorship with goal-setting, regular check-ins, and career development planning. Free for LinkedIn members.",
    "MentorCruise - Cybersecurity": "Browse mentor profiles filtered by specialty (cloud security, pentesting, GRC) and read reviews from past mentees. Typical sessions are weekly for 1-3 months. Pricing varies by mentor experience level.",
    "Cyber Potential": "Career coaching service specifically for cybersecurity professionals. Covers LinkedIn optimization, resume writing, interview preparation, and job search strategy. Offers both 1-on-1 and group coaching packages.",
    "OffSec Talent Finder": "OffSec-certified professionals (OSCP, OSWA, OSEP, OSED) can opt into the talent finder to be discovered by employers. Your certification status and completion metrics serve as verified proof of skills.",
    "r/cybersecurity": "Subreddit with 800K+ members sharing career advice, job leads, news, and technical discussions. Weekly career question threads and mentor-matching posts. Anonymous format encourages candid salary and employer discussions.",
    "r/netsec": "More technically focused subreddit for network and information security professionals. Primarily shares vulnerability research, tool releases, and technical write-ups. Good for staying current with security developments.",
    "Programs.com - Cybersecurity Job Guide 2025": "Provides an honest assessment of the entry-level cybersecurity job market including the impact of AI on hiring. Covers practical strategies for standing out without extensive experience.",
    "DestCert - Cybersecurity Job Demand 2025": "Data-driven analysis of cybersecurity workforce trends, projected demand by specialty through 2030, and the certifications most valued by employers in different industry sectors.",
    "Global Cybersecurity Network Blog": "Regular articles covering job search strategies, interview preparation, and career development tips specific to cybersecurity. Contributors include hiring managers and career coaches from the industry.",
    "Cybersecurity Guide - Job Resources": "Comprehensive guide covering all channels for finding cybersecurity jobs: company career pages, staffing agencies, networking events, internships, and apprenticeship programs. Good for career changers.",
    "HackerOne": "Run by both private companies and government agencies (DoD, GSA). Earn bounties ranging from hundreds to tens of thousands of dollars. Your public profile and reputation score serve as a verified portfolio for employers.",
    "Bugcrowd": "Offers both public and private bug bounty programs. The researcher ranking system and public profile showcase your findings to potential employers. Includes a vulnerability disclosure platform for coordinated disclosure.",
    "Synack": "Invitation-only platform requiring an application and vetting process. Higher-quality targets from enterprise and government clients mean larger payouts. Your Synack Red Team membership is itself a credential.",
}

def add_tooltips(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # For each resource, find '<div class="resource-card">' followed by content
    # containing the h3 text, and add data-tooltip attribute
    changes = 0
    skipped = []

    for name, tooltip in TOOLTIPS.items():
        # Escape for HTML attribute (double quotes and ampersands)
        escaped_tooltip = tooltip.replace('&', '&amp;').replace('"', '&quot;')

        # Find the h3 containing this name
        # Pattern: <div class="resource-card"> ... <h3>NAME</h3>
        # We need to add data-tooltip to the div

        # Find all occurrences of this h3 name
        h3_pattern = re.compile(
            r'<h3>' + re.escape(name) + r'</h3>',
            re.IGNORECASE
        )

        matches = list(h3_pattern.finditer(content))
        if not matches:
            skipped.append(name)
            continue

        # For each match, find the preceding <div class="resource-card">
        # and add data-tooltip if not already present
        for match in reversed(matches):  # Reverse to preserve positions
            h3_pos = match.start()

            # Search backwards for the resource-card div
            search_start = max(0, h3_pos - 500)
            chunk = content[search_start:h3_pos]

            # Find the last occurrence of <div class="resource-card"> in the chunk
            div_pattern = r'<div class="resource-card"'
            div_matches = list(re.finditer(div_pattern, chunk))

            if not div_matches:
                skipped.append(f"{name} (no div found)")
                continue

            last_div = div_matches[-1]
            div_pos = search_start + last_div.start()

            # Check if data-tooltip already exists on this div
            div_end = content.index('>', div_pos)
            div_tag = content[div_pos:div_end + 1]

            if 'data-tooltip' in div_tag:
                continue  # Already has tooltip

            # Insert data-tooltip before the closing >
            # Handle both <div class="resource-card"> and multi-line variants
            insertion_point = div_end
            new_attr = f'\n                            data-tooltip="{escaped_tooltip}"'
            content = content[:insertion_point] + new_attr + content[insertion_point:]
            changes += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Added {changes} tooltips")
    if skipped:
        print(f"Skipped {len(skipped)} resources (not found):")
        for s in skipped:
            print(f"  - {s}")

if __name__ == '__main__':
    add_tooltips('/Users/shawn/csoh.org/resources.html')
