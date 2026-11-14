import os, textwrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DATA = """
Microsurgical operations on the middle ear :: Stapedotomy to treat various lesions in middle ear ## Revision of a stapedectomy ## Other operations on the auditory ossicles ## Myringoplasty / Tympanoplasty ## Revision of a tympanoplasty ## Other microsurgical operations on the middle ear
Other operations on the middle and internal ear :: Myringotomy ## Removal of a tympanic drain ## Mastoidectomy ## Reconstruction of the middle ear ## Fenestration of the inner ear ## Removal of Keratosis Obturans
Operations on the nose and nasal sinuses :: Excision and destruction of diseased tissue of the nose ## Operations on the turbinates (nasal concha) ## Nasal sinus aspiration ## Foreign body removal from nose
Operations on the eyes :: Incision of tear glands ## Other operations on the tear ducts ## Incision of diseased eyelids ## Correction of Eyelid Ptosis by Levator Palpebrae Superioris Resection (Bilateral) ## Correction of Eyelid Ptosis by Fascia Lata Graft (bilateral) ## Excision and destruction of diseased tissue of the eyelid ## Operations on the canthus and epicanthus ## Corrective surgery for entropion and ectropion ## Corrective surgery for blepharoptosis ## Removal of a foreign body from the conjunctiva ## Removal of a foreign body from the cornea ## Incision of the cornea ## Operations for pterygium ## Other operations on the cornea ## Removal of a foreign body from the lens of the eye ## Removal of a foreign body from the posterior chamber of the eye ## Removal of a foreign body from the orbit and eyeball ## Operation of cataract ## Diathermy/Cryotherapy to treat retinal tear ## Anterior chamber Paracentesis/Cyclodiathermy/Cyclocryotherapy ## Goniotomy/Trabeculotomy and Filtering and Allied Operations to treat Glaucoma ## Enucleation of Eye without Implant
Operations on the skin and subcutaneous tissues :: Incision of a pilonidal sinus ## Other incisions of the skin and subcutaneous tissues ## Surgical wound toilet (wound debridement) and removal of diseased tissue of the skin and subcutaneous tissues ## Local Excision of diseased tissue of the skin and subcutaneous tissues ## Other excisions of the skin and subcutaneous tissues ## Simple restoration of surface continuity of the skin and subcutaneous tissues ## Free skin transplantation, donor site ## Free skin transplantation, recipient site ## Revision of skin plasty ## Other restoration and reconstruction of the skin and subcutaneous tissues ## Chemosurgery to the skin ## Destruction of diseased tissue in the skin and subcutaneous tissues ## Reconstruction of Deformity/Defect in Nail Bed
Operations on the tongue :: Incision, excision and destruction of diseased tissue of the tongue ## Partial glossectomy ## Glossectomy ## Reconstruction of the tongue ## Other operations on the tongue
Operations on the salivary glands and salivary ducts :: Incision and lancing of a salivary gland and salivary duct ## Excision of diseased tissue of a salivary gland and a salivary duct ## Resection of a salivary gland ## Reconstruction of a salivary gland and a salivary duct ## Other operations on the salivary glands and salivary ducts
Other operations on the mouth and face :: External incision and drainage in the region of the mouth, jaw and face ## Incision of the hard and soft palate ## Excision and destruction of diseased hard and soft palate ## Incision, excision and destruction in the mouth ## Plastic surgery to the floor of the mouth ## Palatoplasty ## Other operations in the mouth
Operations on tonsils and adenoids :: Transoral incision and drainage of a pharyngeal abscess ## Tonsillectomy without adenoidectomy ## Tonsillectomy with adenoidectomy ## Excision and destruction of a lingual tonsil ## Other operations on the tonsils and adenoids
Trauma surgery and orthopaedics :: Incision on bone, septic and aseptic ## Closed reduction on fracture, luxation or epiphyseolysis with osteosynthesis ## Suture and other operations on tendons and tendon sheath ## Reduction of dislocation under GA ## Arthroscopic Knee aspiration
Operations on the breast :: Incision of the breast abscess ## Operations on the nipple ## Excision of single breast lump
Operations on the digestive tract, kidney and bladder :: Incision and excision of tissue in the perianal region ## Surgical treatment of anal fistulas ## Surgical treatment of hemorrhoids ## Division of the anal sphincter (sphincterotomy) ## Other operations on the anus ## Ultrasound guided aspirations ## Sclerotherapy ## Laparotomy for grading Lymphoma with Splenectomy/Liver/Lymph Node ## Therapeutic Laparoscopy with Laser ## Cholecystectomy and Choledocho-Jejunostomy/Duodenostomy/Gastrostomy/Exploration Common Bile Duct ## Esophagoscopy, gastroscopy, duodenoscopy with polypectomy/removal of foreign body/diathermy of bleeding lesions ## Lithotripsy/Nephrolithotomy for renal calculus ## Excision of renal cyst ## Drainage of Pyonephrosis/Perinephric Abscess
Operations on the female sexual organs :: Incision of the ovary ## Insufflations of the Fallopian tubes ## Other operations on the Fallopian tube ## Dilation of the cervical canal ## Conization of the uterine cervix ## Therapeutic curettage with Colposcopy/Biopsy/Diathermy/Cryosurgery ## Laser Therapy of Cervix for Various lesions of Uterus ## Other operations on the uterine cervix ## Incision of the uterus (hysterectomy) ## Local excision and destruction of diseased tissue of the vagina and the pouch of Douglas ## Incision of vagina ## Incision of vulva ## Culdotomy ## Operations on Bartholin's glands (cyst) ## Salpingo-Oophorectomy via Laparotomy
Operations on the prostate and seminal vesicles :: Incision of the prostate ## Transurethral excision and destruction of prostate tissue ## Transurethral and percutaneous destruction of prostate tissue ## Open surgical excision and destruction of prostate tissue ## Radical prostatovesiculectomy ## Other excision and destruction of prostate tissue ## Operations on the seminal vesicles ## Incision and excision of periprostatic tissue ## Other operations on the prostate
Operations on the scrotum and tunica vaginalis testis :: Incision of the scrotum and tunica vaginalis testis ## Operation on a testicular hydrocele ## Excision and destruction of diseased scrotal tissue ## Plastic reconstruction of the scrotum and tunica vaginalis testis ## Other operations on the scrotum and tunica vaginalis testis
Operations on the testes :: Incision of the testes ## Excision and destruction of diseased tissue of the testes ## Unilateral orchidectomy ## Bilateral orchidectomy ## Orchidopexy ## Abdominal exploration in cryptorchidism ## Surgical repositioning of an abdominal testis ## Reconstruction of the testis ## Implantation, exchange and removal of a testicular prosthesis ## Other operations on the testis
Operations on the spermatic cord, epididymis and ductus deferens :: Surgical treatment of a varicocele and a hydrocele of the spermatic cord ## Excision in the area of the epididymis ## Epididymectomy ## Reconstruction of the spermatic cord ## Reconstruction of the ductus deferens and epididymis ## Other operations on the spermatic cord, epididymis and ductus deferens
Operations on the penis :: Operations on the foreskin ## Local excision and destruction of diseased tissue of the penis ## Plastic reconstruction of the penis ## Amputation of the penis ## Other operations on the penis
Operations on the urinary system :: Cystoscopical removal of stones ## Catheterisation of Bladder
Operations of bones and joints :: Surgery for ligament tear ## Surgery for meniscus tear ## Surgery for hemoarthrosis/pyoarthrosis ## Removal of fracture pins/nails ## Removal of metal wire ## Closed reduction on fracture, luxation ## Reduction of dislocation under GA ## Epiphyseolysis with osteosynthesis ## Excision of Bursitis ## Tennis Elbow Release ## Excision of various Lesions in Coccyx
Other operations :: Lithotripsy ## Coronary angiography ## Biopsy of Temporal Artery for Various Lesions ## External Arterio-venous Shunt ## Haemodialysis ## Radiotherapy for Cancer ## Cancer Chemotherapy ## Endoscopic polypectomy
"""

os.makedirs("data/raw", exist_ok=True)
c = canvas.Canvas("data/raw/daycare.pdf", pagesize=A4)
W, H = A4
y = H - 50
def put(text, bold=False, size=10, indent=0):
    global y
    if y < 50:
        c.showPage(); y = H - 50
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(40 + indent, y, text)
    y -= 20 if bold else 14
put("Care Health Insurance - Day Care Treatments List (source: Plum help docs)", True, 12)
n = 0
for line in DATA.strip().splitlines():
    cat, items = line.split(" :: ")
    y -= 6
    put("Category: " + cat, True, 11)
    for item in items.split(" ## "):
        n += 1
        for k, part in enumerate(textwrap.wrap(f"{n}. {item}", 95)):
            put(part, indent=0 if k == 0 else 14)
c.save()
print("wrote data/raw/daycare.pdf with", n, "procedures")