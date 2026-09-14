from pathlib import Path
p=Path('QS&QA_Fundation/QS&QA_Fundation.tex');s=p.read_bytes().decode('utf-8')
s=s.replace(r'\subsection{QPE، VQD و قطری‌سازی زیرفضای کوانتومی}',r'\subsection{\lr{QPE}، \lr{VQD} و قطری‌سازی زیرفضای کوانتومی}')
s=s.replace('چون مقالهٔ مشخصی در درخواست معرفی نشده، چند مسیر مکمل انتخاب شده‌اند.','برای پوشش نظریه، محاسبه و آزمایش، چند مسیر مکمل انتخاب شده‌اند.')
s=s.replace('ثبات لگاریتمی را نباید','تعداد کیوبیت لگاریتمی را نباید')
s=s.replace('آغاز مناسب‌اند. مرور','آغاز مناسب‌اند.\r\n\r\nمرور')
s=s.replace('و عوامل چندلگاریتمی است.','و عوامل چندلگاریتمی است؛ $\\epsilon$ دقت نسبی گاف در قرارداد نرمال‌سازی مقاله است.')
old='اگر $B$ قطر $h$ و قطر پایین $-J$ داشته باشد، انرژی تحریک‌های مثبت $2\\sigma_j(B)$ هستند؛ کوچک‌ترین آن‌ها گاف کل است.'
new=r'''اگر $B$ قطر $h$ و قطر پایین $-J$ داشته باشد، انرژی تحریک‌های مثبت $2\sigma_j(B)$ هستند؛ کوچک‌ترین آن‌ها گاف کل است.
برای روشن‌شدن این کاهش، پس از تبدیل جردن--ویگنر و قطری‌سازی بوگولیوبوف، هامیلتونی شکل
\begin{equation}
 H=\sum_{j=1}^n\epsilon_j(f_j^\dagger f_j-\tfrac12),\qquad
 \epsilon_j=2\sigma_j(B),\quad \{f_i,f_j^\dagger\}=\delta_{ij}
\end{equation}
دارد. در زنجیرهٔ باز و بدون قید زوجیت، پایه خلأ این شبه‌ذره‌هاست و ارزان‌ترین تحریک یک مد را اشغال می‌کند؛ پس $\Delta=\min_j\epsilon_j$.
این ساده‌شدن حاصل ساختار فرمیون آزاد است؛ افزودن میدان طولی یا برهم‌کنش عمومی معمولاً آن را از بین می‌برد~\cite{GapPfeuty1970}.'''
assert old in s;s=s.replace(old,new.replace('\n','\r\n'))
p.write_bytes(s.encode('utf-8'))
p=Path('QS&QA_Fundation/bibs/quantum_sim.bib')
with p.open('a',encoding='utf-8') as f:f.write(r'''
@article{GapPfeuty1970,
 author={Pfeuty, Pierre},
 title={The one-dimensional {Ising} model with a transverse field},
 journal={Annals of Physics},volume={57},number={1},pages={79--90},year={1970},
 doi={10.1016/0003-4916(70)90270-8}}
''')
for name in ['gap_research_compute.py','gap_spectrum.tex']:
 p=Path('QS&QA_Fundation/figures')/name
 s=p.read_text(encoding='utf-8').replace(r'\node[above left]',r'\node[above left,fill=white,inner sep=1.5pt]')
 p.write_text(s,encoding='utf-8')
print('Final corrections saved')
